"""
SVAS Backend – Smart Volunteer Matching Service
Implements the Haversine-based geo-distance calculation and a weighted
multi-factor scoring algorithm that ranks volunteers against a community need.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Skill → category affinity map
# Each need category lists the skills that match it, in priority order.
_CATEGORY_SKILL_AFFINITY: Dict[str, List[str]] = {
    "FOOD": ["COOKING", "LOGISTICS", "DRIVING", "GENERAL"],
    "HEALTH": ["MEDICAL", "COUNSELING", "DRIVING", "GENERAL"],
    "EDUCATION": ["EDUCATION", "COUNSELING", "GENERAL"],
    "SHELTER": ["LOGISTICS", "DRIVING", "GENERAL"],
    "CLOTHING": ["LOGISTICS", "GENERAL"],
    "OTHER": ["GENERAL", "LOGISTICS"],
}

# Urgency → urgency multiplier applied to the final composite score so that
# high-urgency needs surface the best volunteers more aggressively.
_URGENCY_MULTIPLIER: Dict[str, float] = {
    "HIGH": 1.20,
    "MEDIUM": 1.10,
    "LOW": 1.00,
}

# Maximum distance (km) before the distance component contributes 0 points.
# Override via settings.MATCH_MAX_DISTANCE_KM.
_DEFAULT_MAX_DISTANCE_KM: float = 50.0

# Earth radius used in the Haversine formula (km).
_EARTH_RADIUS_KM: float = 6_371.0


# ---------------------------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------------------------


def calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate the great-circle distance between two points on Earth using the
    Haversine formula.

    Parameters
    ----------
    lat1, lon1 : float
        Latitude and longitude of point 1 (degrees).
    lat2, lon2 : float
        Latitude and longitude of point 2 (degrees).

    Returns
    -------
    float
        Distance in kilometres (always ≥ 0).
    """
    # Convert degrees → radians
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_KM * c


# ---------------------------------------------------------------------------
# Individual scoring components
# ---------------------------------------------------------------------------


def calculate_skill_score(
    volunteer_skills: List[str],
    required_skills: List[str],
    need_category: str = "OTHER",
) -> float:
    """
    Compute how well a volunteer's skills match a need's required skills.

    Scoring logic
    -------------
    1. **Exact required-skill matches** – each required skill that the volunteer
       has contributes ``1 / len(required_skills)`` points (up to 1.0 total).
    2. **Category-affinity bonus** – if no required skills are listed, the
       volunteer's skills are compared against the category affinity map.
       The position of the best matching skill in the affinity list is used
       to produce a score in the range [0.3, 1.0].
    3. A volunteer with no relevant skills at all returns 0.0.

    Parameters
    ----------
    volunteer_skills : list[str]
        Skill strings held by the volunteer (e.g. ``["MEDICAL", "DRIVING"]``).
    required_skills : list[str]
        Skills listed on the need / task.
    need_category : str
        Primary category of the need (used for affinity fallback).

    Returns
    -------
    float
        Score in the range [0.0, 1.0].
    """
    if not volunteer_skills:
        return 0.0

    v_skills = {s.upper() for s in volunteer_skills}
    r_skills = {s.upper() for s in required_skills}

    # ── Direct required-skill match ───────────────────────────────────
    if r_skills:
        matched = v_skills & r_skills
        base_score = len(matched) / len(r_skills)
        # Partial-match bonus: even one skill matching earns at least 0.3
        if matched and base_score < 0.3:
            base_score = 0.3
        return min(base_score, 1.0)

    # ── Category-affinity fallback ────────────────────────────────────
    affinity_list = _CATEGORY_SKILL_AFFINITY.get(need_category.upper(), ["GENERAL"])
    for rank, affinity_skill in enumerate(affinity_list):
        if affinity_skill in v_skills:
            # Earlier ranks (closer to index 0) yield higher scores
            score = max(0.3, 1.0 - rank * 0.15)
            return round(score, 3)

    # Has GENERAL skill → small but non-zero contribution
    if "GENERAL" in v_skills:
        return 0.25

    return 0.0


def calculate_distance_score(
    distance_km: Optional[float],
    max_distance_km: float = _DEFAULT_MAX_DISTANCE_KM,
) -> float:
    """
    Convert a raw distance (km) into a normalised 0→1 proximity score.

    Score decays linearly from 1.0 at 0 km to 0.0 at ``max_distance_km``.
    Beyond ``max_distance_km`` the score is 0.0 (volunteer out of range).
    When distance is unknown (``None``) a neutral value of 0.5 is returned so
    that lack of GPS data doesn't penalise the volunteer too harshly.

    Parameters
    ----------
    distance_km : float or None
        Great-circle distance between volunteer and need site.
    max_distance_km : float
        Distance threshold beyond which the score is 0.

    Returns
    -------
    float
        Score in [0.0, 1.0].
    """
    if distance_km is None:
        return 0.5  # neutral – no GPS data

    if distance_km <= 0:
        return 1.0

    if distance_km >= max_distance_km:
        return 0.0

    return round(1.0 - (distance_km / max_distance_km), 4)


def calculate_workload_score(active_tasks: int, max_active_tasks: int = 3) -> float:
    """
    Score a volunteer's current workload.

    A volunteer with 0 active tasks gets a perfect 1.0.
    A volunteer at their task capacity (``max_active_tasks``) gets 0.0.
    Scores are clamped to [0.0, 1.0].

    Parameters
    ----------
    active_tasks : int
        Number of tasks the volunteer is currently handling.
    max_active_tasks : int
        The volunteer's self-declared maximum.

    Returns
    -------
    float
        Score in [0.0, 1.0].
    """
    if max_active_tasks <= 0:
        return 0.0

    ratio = active_tasks / max_active_tasks
    return round(max(0.0, 1.0 - ratio), 4)


# ---------------------------------------------------------------------------
# Composite match score
# ---------------------------------------------------------------------------


def calculate_match_score(
    volunteer: Dict[str, Any],
    need: Dict[str, Any],
    max_distance_km: Optional[float] = None,
) -> Tuple[float, Dict[str, float], Optional[float]]:
    """
    Compute the weighted composite match score for a (volunteer, need) pair.

    Weights (from settings, defaults to):
        - Skill match  : 40 %
        - Distance     : 30 %
        - Availability : 20 %
        - Workload     : 10 %

    Parameters
    ----------
    volunteer : dict
        Volunteer document from Firestore (must include at least ``skills``,
        ``availability``, ``active_tasks``, and optionally ``latitude``,
        ``longitude``, ``max_active_tasks``).
    need : dict
        Need document from Firestore (must include ``category``,
        ``recommended_skills``, and optionally ``latitude``, ``longitude``).
    max_distance_km : float, optional
        Override the maximum distance threshold.

    Returns
    -------
    (composite_score, component_scores, distance_km)
        - composite_score  : float in [0.0, 1.0]
        - component_scores : dict with keys skill, distance, availability, workload
        - distance_km      : float or None
    """
    max_dist = max_distance_km or settings.MATCH_MAX_DISTANCE_KM

    # ── 1. Availability check ─────────────────────────────────────────
    is_available: bool = volunteer.get("availability", False)
    availability_score: float = 1.0 if is_available else 0.0

    # Hard gate: unavailable volunteer cannot be assigned
    if not is_available:
        return (
            0.0,
            {
                "skill": 0.0,
                "distance": 0.0,
                "availability": 0.0,
                "workload": 0.0,
            },
            None,
        )

    # ── 2. Skill score ────────────────────────────────────────────────
    v_skills: List[str] = volunteer.get("skills", [])
    r_skills: List[str] = need.get("recommended_skills", [])
    n_category: str = need.get("category", "OTHER")
    skill_score = calculate_skill_score(v_skills, r_skills, n_category)

    # ── 3. Distance score ─────────────────────────────────────────────
    distance_km: Optional[float] = None
    v_lat = volunteer.get("latitude")
    v_lng = volunteer.get("longitude")
    n_lat = need.get("latitude")
    n_lng = need.get("longitude")

    if all(v is not None for v in [v_lat, v_lng, n_lat, n_lng]):
        distance_km = calculate_distance(
            float(v_lat), float(v_lng), float(n_lat), float(n_lng)
        )
    dist_score = calculate_distance_score(distance_km, max_dist)

    # ── 4. Workload score ─────────────────────────────────────────────
    active = int(volunteer.get("active_tasks", 0))
    max_active = int(volunteer.get("max_active_tasks", 3))
    workload_score = calculate_workload_score(active, max_active)

    # ── 5. Weighted composite ─────────────────────────────────────────
    w_skill = settings.MATCH_WEIGHT_SKILL
    w_dist = settings.MATCH_WEIGHT_DISTANCE
    w_avail = settings.MATCH_WEIGHT_AVAILABILITY
    w_work = settings.MATCH_WEIGHT_WORKLOAD

    composite = (
        w_skill * skill_score
        + w_dist * dist_score
        + w_avail * availability_score
        + w_work * workload_score
    )

    # Apply urgency multiplier (capped at 1.0 so score stays normalised)
    urgency = need.get("urgency", "LOW").upper()
    multiplier = _URGENCY_MULTIPLIER.get(urgency, 1.0)
    composite = min(composite * multiplier, 1.0)

    component_scores = {
        "skill": round(skill_score, 4),
        "distance": round(dist_score, 4),
        "availability": round(availability_score, 4),
        "workload": round(workload_score, 4),
    }

    return round(composite, 4), component_scores, distance_km


# ---------------------------------------------------------------------------
# Human-readable match reasons
# ---------------------------------------------------------------------------


def _build_match_reasons(
    volunteer: Dict[str, Any],
    need: Dict[str, Any],
    component_scores: Dict[str, float],
    distance_km: Optional[float],
) -> List[str]:
    """
    Generate a list of plain-English sentences explaining why this volunteer
    was matched to this need.

    Parameters
    ----------
    volunteer : dict
        Volunteer Firestore document.
    need : dict
        Need Firestore document.
    component_scores : dict
        Individual score components from ``calculate_match_score``.
    distance_km : float or None
        Calculated distance between volunteer and need.

    Returns
    -------
    list[str]
        Up to 5 concise reason strings.
    """
    reasons: List[str] = []

    # ── Skills ────────────────────────────────────────────────────────
    v_skills = [s.upper() for s in volunteer.get("skills", [])]
    r_skills = [s.upper() for s in need.get("recommended_skills", [])]
    n_cat = need.get("category", "OTHER").upper()

    matched_skills = set(v_skills) & set(r_skills)
    if matched_skills:
        reasons.append(
            f"Matches required skill(s): {', '.join(sorted(matched_skills))}"
        )
    elif v_skills:
        affinity = _CATEGORY_SKILL_AFFINITY.get(n_cat, [])
        affinity_match = [s for s in v_skills if s in affinity]
        if affinity_match:
            reasons.append(
                f"Skills ({', '.join(affinity_match)}) are suited for {n_cat} needs"
            )

    # ── Distance ──────────────────────────────────────────────────────
    if distance_km is not None:
        if distance_km < 1:
            reasons.append("Located less than 1 km from the need site")
        elif distance_km < 5:
            reasons.append(f"Very close to need site ({distance_km:.1f} km away)")
        elif distance_km < 20:
            reasons.append(f"Within practical travel distance ({distance_km:.1f} km)")
        else:
            reasons.append(f"Located {distance_km:.1f} km from the need site")
    else:
        reasons.append("GPS location data not available – matched on skills")

    # ── Availability ──────────────────────────────────────────────────
    active = int(volunteer.get("active_tasks", 0))
    if active == 0:
        reasons.append("Currently free – no active tasks assigned")
    elif active == 1:
        reasons.append("Has only 1 active task – has capacity for more")
    else:
        reasons.append(f"Has {active} active task(s) – still within capacity")

    # ── Rating ────────────────────────────────────────────────────────
    rating = volunteer.get("rating")
    if rating and float(rating) >= 4.0:
        reasons.append(
            f"Highly rated volunteer ({rating:.1f} ★ across "
            f"{volunteer.get('rating_count', 0)} task(s))"
        )

    # ── Task history ──────────────────────────────────────────────────
    completed = int(volunteer.get("tasks_completed", 0))
    if completed >= 10:
        reasons.append(f"Experienced – {completed} tasks completed")

    return reasons[:5]  # cap at 5 reasons for readability


# ---------------------------------------------------------------------------
# MatchingService – main public class
# ---------------------------------------------------------------------------


class MatchingService:
    """
    High-level service that orchestrates volunteer matching for a given need.

    Usage
    -----
    ::

        svc = MatchingService()
        results = await svc.find_best_volunteers(need_dict, volunteers_list)
    """

    def __init__(
        self,
        max_distance_km: Optional[float] = None,
        top_n: Optional[int] = None,
    ) -> None:
        self._max_dist = max_distance_km or settings.MATCH_MAX_DISTANCE_KM
        self._top_n = top_n or settings.MATCH_TOP_N

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def find_best_volunteers(
        self,
        need: Dict[str, Any],
        volunteers: List[Dict[str, Any]],
        top_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rank ``volunteers`` against a ``need`` and return the top-N matches.

        Each result dict contains the original volunteer document enriched with:
        - ``score``         : float composite match score (0–1)
        - ``rank``          : int position in the sorted results (1 = best)
        - ``distance_km``   : float or None
        - ``skill_score``   : float
        - ``distance_score``: float
        - ``workload_score``: float
        - ``match_reasons`` : list[str]

        Parameters
        ----------
        need : dict
            Firestore need document.
        volunteers : list[dict]
            Pool of candidate volunteer documents.
        top_n : int, optional
            Override the default ``MATCH_TOP_N`` setting.

        Returns
        -------
        list[dict]
            Sorted (best first) list of enriched volunteer dicts.
            Never longer than ``top_n``.
        """
        n = top_n or self._top_n
        if not volunteers:
            logger.info("find_best_volunteers: volunteer pool is empty.")
            return []

        # Score every volunteer (CPU-bound but fast enough for typical pool sizes)
        scored: List[Tuple[float, Dict[str, Any]]] = []

        for vol in volunteers:
            try:
                composite, components, distance_km = calculate_match_score(
                    vol, need, self._max_dist
                )
                if composite <= 0.0:
                    continue  # skip unavailable or zero-score volunteers

                reasons = _build_match_reasons(vol, need, components, distance_km)

                enriched = {
                    **vol,
                    "score": composite,
                    "distance_km": round(distance_km, 2)
                    if distance_km is not None
                    else None,
                    "skill_score": components["skill"],
                    "distance_score": components["distance"],
                    "workload_score": components["workload"],
                    "match_reasons": reasons,
                }
                scored.append((composite, enriched))

            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Skipping volunteer %s due to scoring error: %s",
                    vol.get("id", "unknown"),
                    exc,
                )
                continue

        # Sort descending by composite score
        scored.sort(key=lambda t: t[0], reverse=True)

        # Add rank and trim to top_n
        results = []
        for rank, (_, enriched) in enumerate(scored[:n], start=1):
            enriched["rank"] = rank
            results.append(enriched)

        logger.info(
            "find_best_volunteers: scored %d/%d volunteers for need '%s', returning top %d",
            len(scored),
            len(volunteers),
            need.get("title", need.get("id", "?")),
            len(results),
        )
        return results

    async def auto_assign(
        self,
        need_id: str,
        firestore_service,  # FirestoreService – passed to avoid circular import
    ) -> Optional[Dict[str, Any]]:
        """
        Automatically assign the best available volunteer to a need.

        Workflow
        --------
        1. Fetch the need document from Firestore.
        2. Fetch all available volunteers.
        3. Run ``find_best_volunteers`` with ``top_n=1``.
        4. Update the volunteer's ``active_tasks`` counter.
        5. Update the need's ``status`` → ASSIGNED and ``assigned_volunteer_ids``.
        6. Create a Task document linking the need and the volunteer.
        7. Return the created Task document dict.

        Parameters
        ----------
        need_id : str
            Firestore document ID of the need to assign.
        firestore_service : FirestoreService
            Shared Firestore service instance.

        Returns
        -------
        dict or None
            The newly created Task document, or ``None`` if no suitable
            volunteer was found.
        """
        from app.config.settings import (
            settings as cfg,  # local import to avoid circulars
        )

        # 1. Fetch need
        need = await firestore_service.get_document(cfg.COLLECTION_NEEDS, need_id)
        if not need:
            logger.warning("auto_assign: need '%s' not found.", need_id)
            return None

        # 2. Fetch available volunteers
        volunteers = await firestore_service.get_available_volunteers(limit=200)
        if not volunteers:
            logger.warning("auto_assign: no available volunteers in the pool.")
            return None

        # 3. Find best match
        matches = await self.find_best_volunteers(need, volunteers, top_n=1)
        if not matches:
            logger.warning(
                "auto_assign: no suitable volunteer found for need '%s'.", need_id
            )
            return None

        best = matches[0]
        volunteer_id: str = best.get("id") or best.get("uid", "")

        # 4 & 5. Update volunteer workload + need status (concurrently)
        now = datetime.utcnow()
        await asyncio.gather(
            firestore_service.increment_volunteer_active_tasks(volunteer_id, delta=1),
            firestore_service.update_document(
                cfg.COLLECTION_NEEDS,
                need_id,
                {
                    "status": "ASSIGNED",
                    "assigned_volunteer_ids": [volunteer_id],
                    "updated_at": now,
                },
            ),
        )

        # 6. Create Task document
        task_data: Dict[str, Any] = {
            "need_id": need_id,
            "title": f"[Auto] {need.get('title', 'Task')}",
            "description": need.get("description", ""),
            "category": need.get("category", "OTHER"),
            "urgency": need.get("urgency", "MEDIUM"),
            "priority": need.get("urgency", "MEDIUM"),
            "location": need.get("location", ""),
            "latitude": need.get("latitude"),
            "longitude": need.get("longitude"),
            "assigned_volunteer_id": volunteer_id,
            "assigned_by": "system",
            "required_skills": need.get("recommended_skills", []),
            "beneficiary_count": need.get("beneficiary_count"),
            "status": "ASSIGNED",
            "is_auto_assigned": True,
            "match_score": best.get("score"),
            "match_reasons": best.get("match_reasons", []),
            "assigned_at": now,
            "created_at": now,
            "updated_at": now,
        }

        task_id = await firestore_service.create_document(
            cfg.COLLECTION_TASKS, task_data
        )
        task_data["id"] = task_id

        logger.info(
            "auto_assign: created task '%s' assigning volunteer '%s' to need '%s' (score=%.3f)",
            task_id,
            volunteer_id,
            need_id,
            best.get("score", 0),
        )
        return task_data

    # ------------------------------------------------------------------
    # Utility helpers (exposed for testing / API use)
    # ------------------------------------------------------------------

    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Public alias for the module-level ``calculate_distance`` function."""
        return calculate_distance(lat1, lon1, lat2, lon2)

    @staticmethod
    def score_pair(
        volunteer: Dict[str, Any],
        need: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Score a single volunteer–need pair and return a detailed breakdown dict.
        Convenience wrapper for use in tests and one-off API calls.
        """
        composite, components, distance_km = calculate_match_score(volunteer, need)
        reasons = _build_match_reasons(volunteer, need, components, distance_km)
        return {
            "composite_score": composite,
            "skill_score": components["skill"],
            "distance_score": components["distance"],
            "availability_score": components["availability"],
            "workload_score": components["workload"],
            "distance_km": round(distance_km, 2) if distance_km is not None else None,
            "match_reasons": reasons,
        }
