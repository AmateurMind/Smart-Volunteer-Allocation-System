"""
SVAS Backend – /dashboard Router
Aggregates real-time statistics, heatmap data, and recent activity from
Firestore for the frontend decision dashboard.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.middleware.auth import get_current_user
from app.services.bigquery_service import BigQueryService
from app.services.firestore_service import FirestoreService
from fastapi import APIRouter, Depends, Query, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# ── Shared service singletons ─────────────────────────────────────────────────
_firestore: Optional[FirestoreService] = None
_bigquery: Optional[BigQueryService] = None


def _get_firestore() -> FirestoreService:
    global _firestore
    if _firestore is None:
        _firestore = FirestoreService()
    return _firestore


def _get_bigquery() -> BigQueryService:
    global _bigquery
    if _bigquery is None:
        _bigquery = BigQueryService()
    return _bigquery


# ── Helpers ───────────────────────────────────────────────────────────────────


def _safe_serialize(obj: Any) -> Any:
    """Recursively convert non-JSON-serialisable types to safe equivalents."""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_serialize(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def _count_by_field(docs: List[Dict[str, Any]], field: str) -> Dict[str, int]:
    """Return a frequency dict for a given field across all documents."""
    counts: Dict[str, int] = {}
    for doc in docs:
        val = doc.get(field, "UNKNOWN")
        counts[val] = counts.get(val, 0) + 1
    return counts


def _is_today(dt_value: Any) -> bool:
    """Return True if *dt_value* is a datetime on today's UTC date."""
    if isinstance(dt_value, datetime):
        return dt_value.date() == datetime.utcnow().date()
    return False


# ─────────────────────────────────────────────────────────────────────────────
# GET /dashboard
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Full dashboard data",
    description=(
        "Returns a comprehensive snapshot of the platform state: "
        "need breakdowns, task status counts, volunteer availability, "
        "heatmap points, and recent activity feeds.\n\n"
        "This is the primary endpoint consumed by the dashboard page."
    ),
)
async def get_dashboard(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Aggregate dashboard data from Firestore in a single call.

    Response shape
    --------------
    ::

        {
          "needs_by_category":  { "FOOD": 12, "HEALTH": 5, … },
          "needs_by_urgency":   { "HIGH": 8, "MEDIUM": 6, "LOW": 3 },
          "needs_by_status":    { "OPEN": 10, "ASSIGNED": 5, … },
          "tasks_by_status":    { "PENDING": 3, "ASSIGNED": 7, … },
          "total_needs":        17,
          "total_tasks":        10,
          "total_volunteers":   42,
          "available_volunteers": 35,
          "recent_needs":       [ … ],
          "recent_tasks":       [ … ],
          "heatmap_points":     [ {"lat":…, "lng":…, "weight":…, "category":…} ],
          "generated_at":       "2024-07-15T10:00:00"
        }
    """
    fs = _get_firestore()

    try:
        stats = await fs.get_dashboard_stats()
    except Exception as exc:
        logger.error("get_dashboard: Firestore aggregation failed: %s", exc)
        # Return a graceful empty payload rather than a 500 error
        stats = {
            "needs_by_category": {},
            "needs_by_urgency": {},
            "needs_by_status": {},
            "tasks_by_status": {},
            "total_needs": 0,
            "total_tasks": 0,
            "total_volunteers": 0,
            "available_volunteers": 0,
            "recent_needs": [],
            "recent_tasks": [],
            "heatmap_points": [],
        }

    stats["generated_at"] = datetime.utcnow().isoformat()
    return _safe_serialize(stats)


# ─────────────────────────────────────────────────────────────────────────────
# GET /dashboard/stats
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Quick KPI statistics",
    description=(
        "Lightweight stats endpoint returning the four headline KPIs "
        "shown in the top stat-cards of the dashboard: "
        "total open needs, active volunteers, tasks in progress, and tasks "
        "completed today."
    ),
)
async def get_stats(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Return the four headline KPI numbers for the dashboard stat cards.

    Response shape
    --------------
    ::

        {
          "open_needs":           10,
          "active_volunteers":    35,
          "tasks_in_progress":    4,
          "completed_today":      2,
          "high_urgency_needs":   3,
          "pending_assignments":  7,
          "total_beneficiaries":  450,
          "generated_at":         "…"
        }
    """
    fs = _get_firestore()

    try:
        # Fetch the collections we need concurrently
        import asyncio

        open_needs, in_progress_tasks, all_tasks, available_vols = await asyncio.gather(
            fs.get_open_needs(limit=500),
            fs.get_tasks_by_status("IN_PROGRESS", limit=500),
            fs.get_all_documents(settings.COLLECTION_TASKS, limit=500),
            fs.get_available_volunteers(limit=500),
        )

        # Completed today
        completed_today = sum(
            1
            for t in all_tasks
            if t.get("status") == "COMPLETED" and _is_today(t.get("completed_at"))
        )

        # High urgency open needs
        high_urgency = sum(1 for n in open_needs if n.get("urgency") == "HIGH")

        # Pending (created but not yet assigned)
        pending = sum(1 for t in all_tasks if t.get("status") == "PENDING")

        # Estimated total beneficiaries across all open needs
        total_beneficiaries = sum(
            int(n.get("beneficiary_count") or 0) for n in open_needs
        )

    except Exception as exc:
        logger.error("get_stats: aggregation failed: %s", exc)
        return {
            "open_needs": 0,
            "active_volunteers": 0,
            "tasks_in_progress": 0,
            "completed_today": 0,
            "high_urgency_needs": 0,
            "pending_assignments": 0,
            "total_beneficiaries": 0,
            "generated_at": datetime.utcnow().isoformat(),
            "error": "Could not fetch statistics at this time.",
        }

    return {
        "open_needs": len(open_needs),
        "active_volunteers": len(available_vols),
        "tasks_in_progress": len(in_progress_tasks),
        "completed_today": completed_today,
        "high_urgency_needs": high_urgency,
        "pending_assignments": pending,
        "total_beneficiaries": total_beneficiaries,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /dashboard/heatmap
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/heatmap",
    status_code=status.HTTP_200_OK,
    summary="Need heatmap data",
    description=(
        "Returns a list of geo-points for all open needs that have GPS "
        "coordinates.  Each point carries a ``weight`` (1–3 based on "
        "urgency) and a ``category`` so the map layer can colour them "
        "appropriately.\n\n"
        "Use this endpoint to power the Leaflet / Google Maps heatmap layer."
    ),
)
async def get_heatmap(
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter needs by status. Defaults to OPEN.",
    ),
    category: Optional[str] = Query(
        default=None,
        description="Filter by category (FOOD, HEALTH, …).",
    ),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Return geo-points for the need heatmap layer.

    Each point has:
    - ``lat``      : float – latitude
    - ``lng``      : float – longitude
    - ``weight``   : float – 3.0 (HIGH), 2.0 (MEDIUM), 1.0 (LOW)
    - ``category`` : str
    - ``urgency``  : str
    - ``title``    : str
    - ``id``       : str – Firestore document ID
    - ``beneficiary_count`` : int or null
    """
    fs = _get_firestore()

    filters = []
    target_status = (status_filter or "OPEN").upper()
    filters.append(("status", "==", target_status))
    if category:
        filters.append(("category", "==", category.upper()))

    try:
        needs = await fs.query_collection(
            settings.COLLECTION_NEEDS,
            filters=filters,
            limit=500,
        )
    except Exception as exc:
        logger.error("get_heatmap: Firestore query failed: %s", exc)
        return {"points": [], "count": 0}

    urgency_weight = {"HIGH": 3.0, "MEDIUM": 2.0, "LOW": 1.0}

    points = [
        {
            "id": n.get("id"),
            "lat": n["latitude"],
            "lng": n["longitude"],
            "weight": urgency_weight.get(n.get("urgency", "LOW"), 1.0),
            "category": n.get("category", "OTHER"),
            "urgency": n.get("urgency", "LOW"),
            "title": n.get("title", "Community Need"),
            "location": n.get("location", ""),
            "beneficiary_count": n.get("beneficiary_count"),
        }
        for n in needs
        if n.get("latitude") is not None and n.get("longitude") is not None
    ]

    return {
        "points": points,
        "count": len(points),
        "total_needs": len(needs),
        "needs_without_coords": len(needs) - len(points),
        "status_filter": target_status,
        "category_filter": category,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /dashboard/recent-activity
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/recent-activity",
    status_code=status.HTTP_200_OK,
    summary="Recent platform activity feed",
    description=(
        "Returns the most recent needs, tasks, and volunteer registrations "
        "for the activity feed widget on the dashboard."
    ),
)
async def get_recent_activity(
    limit: int = Query(default=10, ge=1, le=50, description="Items per feed type"),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Return recent activity across needs, tasks, and volunteers.

    Response shape
    --------------
    ::

        {
          "recent_needs":      [ … ],   // newest needs first
          "recent_tasks":      [ … ],   // newest tasks first
          "recent_volunteers": [ … ],   // newest registrations first
        }
    """
    fs = _get_firestore()

    import asyncio

    try:
        recent_needs, recent_tasks, recent_volunteers = await asyncio.gather(
            fs.query_collection(
                settings.COLLECTION_NEEDS,
                order_by="created_at",
                descending=True,
                limit=limit,
            ),
            fs.query_collection(
                settings.COLLECTION_TASKS,
                order_by="created_at",
                descending=True,
                limit=limit,
            ),
            fs.query_collection(
                settings.COLLECTION_VOLUNTEERS,
                order_by="created_at",
                descending=True,
                limit=limit,
            ),
        )
    except Exception as exc:
        logger.error("get_recent_activity: query failed: %s", exc)
        return {
            "recent_needs": [],
            "recent_tasks": [],
            "recent_volunteers": [],
        }

    return _safe_serialize(
        {
            "recent_needs": recent_needs,
            "recent_tasks": recent_tasks,
            "recent_volunteers": recent_volunteers,
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /dashboard/analytics
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/analytics",
    status_code=status.HTTP_200_OK,
    summary="BigQuery analytics overview",
    description=(
        "Fetches analytical data from BigQuery: need trends, completion rates, "
        "category breakdowns, and NGO performance summary.\n\n"
        "Falls back to empty data when BigQuery is not configured."
    ),
)
async def get_analytics(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Look-back window in days.",
    ),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Aggregate analytics from BigQuery for the reports / analytics section.

    Response shape
    --------------
    ::

        {
          "need_trends":        [ {"date": "…", "category": "…", "count": N} ],
          "completion_rates":   { "total_assigned": N, "completion_rate": 0.82, … },
          "category_breakdown": [ {"category": "FOOD", "count": 12, …} ],
          "daily_activity":     [ {"date": "…", "needs_created": N, …} ],
          "ngo_performance":    { "resolution_rate": 0.75, … },
          "period_days":        30
        }
    """
    bq = _get_bigquery()

    import asyncio

    try:
        (
            need_trends,
            completion_rates,
            category_breakdown,
            daily_activity,
            ngo_performance,
        ) = await asyncio.gather(
            bq.get_need_trends(days=days),
            bq.get_completion_rates(days=days),
            bq.get_category_breakdown(days=days),
            bq.get_daily_activity(days=min(days, 14)),
            bq.get_ngo_performance_summary(days=days),
        )
    except Exception as exc:
        logger.error("get_analytics: BigQuery aggregation failed: %s", exc)
        need_trends = []
        completion_rates = {}
        category_breakdown = []
        daily_activity = []
        ngo_performance = {}

    return {
        "need_trends": need_trends,
        "completion_rates": completion_rates,
        "category_breakdown": category_breakdown,
        "daily_activity": daily_activity,
        "ngo_performance": ngo_performance,
        "period_days": days,
        "bq_available": bq.is_ready,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /dashboard/volunteer-distribution
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/volunteer-distribution",
    status_code=status.HTTP_200_OK,
    summary="Volunteer distribution data",
    description=(
        "Returns volunteer counts grouped by skill set and location, "
        "useful for the volunteer distribution map / chart."
    ),
)
async def get_volunteer_distribution(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Break down volunteers by skill, availability, and status.

    Response shape
    --------------
    ::

        {
          "by_skill":        { "MEDICAL": 8, "LOGISTICS": 14, … },
          "by_status":       { "AVAILABLE": 35, "ON_ASSIGNMENT": 6, … },
          "by_availability": { "available": 35, "unavailable": 7 },
          "geo_points":      [ {"lat": …, "lng": …, "name": "…", …} ],
          "total":           42
        }
    """
    fs = _get_firestore()

    try:
        volunteers = await fs.get_all_documents(
            settings.COLLECTION_VOLUNTEERS, limit=500
        )
    except Exception as exc:
        logger.error("get_volunteer_distribution: query failed: %s", exc)
        return {
            "by_skill": {},
            "by_status": {},
            "by_availability": {"available": 0, "unavailable": 0},
            "geo_points": [],
            "total": 0,
        }

    # ── Skill breakdown ───────────────────────────────────────────────
    skill_counts: Dict[str, int] = {}
    for vol in volunteers:
        for skill in vol.get("skills", []):
            skill_counts[skill] = skill_counts.get(skill, 0) + 1

    # ── Status breakdown ──────────────────────────────────────────────
    status_counts = _count_by_field(volunteers, "status")

    # ── Availability ──────────────────────────────────────────────────
    available_count = sum(1 for v in volunteers if v.get("availability") is True)
    unavailable_count = len(volunteers) - available_count

    # ── Geo-points for map ────────────────────────────────────────────
    geo_points = [
        {
            "id": v.get("id"),
            "lat": v["latitude"],
            "lng": v["longitude"],
            "name": v.get("name", "Volunteer"),
            "skills": v.get("skills", []),
            "availability": v.get("availability", False),
            "active_tasks": v.get("active_tasks", 0),
        }
        for v in volunteers
        if v.get("latitude") is not None and v.get("longitude") is not None
    ]

    return {
        "by_skill": skill_counts,
        "by_status": status_counts,
        "by_availability": {
            "available": available_count,
            "unavailable": unavailable_count,
        },
        "geo_points": _safe_serialize(geo_points),
        "total": len(volunteers),
    }
