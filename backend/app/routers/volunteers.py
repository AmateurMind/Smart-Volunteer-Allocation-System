"""
SVAS Backend – /volunteer Router
Volunteer registration, profile management, and task history endpoints.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.middleware.auth import get_current_user, set_user_role
from app.models.volunteer import VolunteerCreate, VolunteerUpdate
from app.services.bigquery_service import BigQueryService, EventType
from app.services.fcm_service import FCMService
from app.services.firestore_service import FirestoreService
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/volunteer", tags=["Volunteers"])

# ── Service singletons ────────────────────────────────────────────────────────

_firestore: Optional[FirestoreService] = None
_fcm: Optional[FCMService] = None
_bigquery: Optional[BigQueryService] = None


def _get_firestore() -> FirestoreService:
    global _firestore
    if _firestore is None:
        _firestore = FirestoreService()
    return _firestore


def _get_fcm() -> FCMService:
    global _fcm
    if _fcm is None:
        _fcm = FCMService()
    return _fcm


def _get_bigquery() -> BigQueryService:
    global _bigquery
    if _bigquery is None:
        _bigquery = BigQueryService()
    return _bigquery


# ── Helpers ───────────────────────────────────────────────────────────────────


def _safe_dt(data: Any) -> Any:
    """Recursively convert datetime objects to ISO strings."""
    if isinstance(data, dict):
        return {k: _safe_dt(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_safe_dt(v) for v in data]
    if isinstance(data, datetime):
        return data.isoformat()
    return data


def _paginate(items: List[Any], page: int, page_size: int) -> Dict[str, Any]:
    """Slice a list and return pagination metadata."""
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]
    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "has_next": end < total,
        "has_prev": page > 1,
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /volunteer/register
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new volunteer",
    description=(
        "Create a volunteer profile for the currently authenticated user. "
        "Sets the user's role to VOLUNTEER in Firebase custom claims and "
        "creates a document in the Firestore `volunteers` collection. "
        "Optionally sends a welcome FCM push notification."
    ),
)
async def register_volunteer(
    payload: VolunteerCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Register the authenticated user as a volunteer.

    Steps
    -----
    1. Validate that a volunteer profile doesn't already exist for this UID.
    2. Create the volunteer document in Firestore (doc ID = UID).
    3. Update the user document's role to VOLUNTEER.
    4. Set the Firebase custom claim ``role=VOLUNTEER``.
    5. Send a welcome FCM notification if an FCM token is present.
    6. Log ``VOLUNTEER_REGISTERED`` event to BigQuery.
    """
    fs = _get_firestore()
    fcm = _get_fcm()
    bq = _get_bigquery()
    uid: str = current_user.get("uid", payload.uid)

    # ── 1. Check for duplicate registration ──────────────────────────
    existing = await fs.get_document(settings.COLLECTION_VOLUNTEERS, uid)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A volunteer profile already exists for UID '{uid}'. "
                "Use PUT /volunteer/{id} to update your profile."
            ),
        )

    # ── 2. Build and persist the Firestore document ───────────────────
    now = datetime.utcnow()
    vol_data: Dict[str, Any] = {
        **payload.model_dump(exclude_none=False),
        "uid": uid,  # always use the token UID
        "status": "AVAILABLE",
        "tasks_completed": 0,
        "active_tasks": 0,
        "rating": None,
        "rating_count": 0,
        "created_at": now,
        "updated_at": now,
        "last_active_at": now,
    }

    # Normalise skill strings to uppercase
    vol_data["skills"] = [s.upper() for s in (vol_data.get("skills") or [])]

    try:
        # Use the UID as the document ID so lookups are O(1)
        doc_id = await fs.set_document(
            settings.COLLECTION_VOLUNTEERS, uid, vol_data, merge=False
        )
    except Exception as exc:
        logger.error("register_volunteer: Firestore write failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create volunteer profile: {exc}",
        ) from exc

    # ── 3. Update user document role ──────────────────────────────────
    try:
        await fs.set_document(
            settings.COLLECTION_USERS,
            uid,
            {
                "uid": uid,
                "email": payload.email,
                "name": payload.name,
                "role": "VOLUNTEER",
                "phone": payload.phone,
                "location": payload.location,
                "fcm_token": payload.fcm_token,
                "updated_at": now,
            },
            merge=True,
        )
    except Exception as exc:
        logger.warning("register_volunteer: failed to update user doc: %s", exc)

    # ── 4. Set Firebase custom claim ──────────────────────────────────
    try:
        set_user_role(uid, "VOLUNTEER")
    except Exception as exc:
        logger.warning("register_volunteer: failed to set custom claim: %s", exc)

    # ── 5. Welcome notification (background) ─────────────────────────
    if payload.fcm_token:
        background_tasks.add_task(
            fcm.send_welcome,
            volunteer_token=payload.fcm_token,
            volunteer_name=payload.name,
        )

    # ── 6. BigQuery log (background) ─────────────────────────────────
    background_tasks.add_task(
        bq.log_event,
        EventType.VOLUNTEER_REGISTERED,
        {
            "user_uid": uid,
            "volunteer_id": uid,
            "location": payload.location,
        },
    )

    logger.info(
        "register_volunteer: profile created for '%s' (uid=%s)", payload.name, uid
    )

    return {
        "success": True,
        "message": f"Volunteer profile created for '{payload.name}'.",
        "volunteer_id": doc_id,
        "volunteer": _safe_dt(vol_data),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /volunteer/list
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/list",
    status_code=status.HTTP_200_OK,
    summary="List all volunteers",
    description=(
        "Return all volunteer profiles with optional filtering by skill, "
        "availability, and location query string. Supports pagination."
    ),
)
async def list_volunteers(
    page: int = Query(default=1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page."),
    skill: Optional[str] = Query(
        default=None,
        description="Filter volunteers who have this skill (e.g. MEDICAL).",
    ),
    available_only: bool = Query(
        default=False,
        description="If True, return only volunteers where availability=True.",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Case-insensitive substring search on volunteer name or location.",
    ),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Return a paginated list of volunteer profiles.

    Filtering is applied client-side after a Firestore fetch because Firestore
    does not support full-text search or ``ARRAY_CONTAINS`` combined with
    ``==`` filters on different fields simultaneously.
    """
    fs = _get_firestore()

    # Build Firestore filters (only simple equality filters)
    fs_filters = []
    if available_only:
        fs_filters.append(("availability", "==", True))

    try:
        volunteers = await fs.query_collection(
            settings.COLLECTION_VOLUNTEERS,
            filters=fs_filters if fs_filters else None,
            order_by="created_at",
            descending=True,
            limit=500,  # fetch up to 500 then filter/paginate in Python
        )
    except Exception as exc:
        logger.error("list_volunteers: query failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve volunteers.",
        ) from exc

    # ── Client-side filters ───────────────────────────────────────────
    if skill:
        skill_upper = skill.upper()
        volunteers = [
            v
            for v in volunteers
            if skill_upper in [s.upper() for s in (v.get("skills") or [])]
        ]

    if search:
        search_lower = search.lower()
        volunteers = [
            v
            for v in volunteers
            if search_lower in (v.get("name") or "").lower()
            or search_lower in (v.get("location") or "").lower()
        ]

    # ── Pagination ────────────────────────────────────────────────────
    paginated = _paginate(volunteers, page, page_size)

    return {
        "volunteers": _safe_dt(paginated["items"]),
        "total": paginated["total"],
        "page": paginated["page"],
        "page_size": paginated["page_size"],
        "total_pages": paginated["total_pages"],
        "has_next": paginated["has_next"],
        "has_prev": paginated["has_prev"],
        "filters_applied": {
            "skill": skill,
            "available_only": available_only,
            "search": search,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /volunteer/me
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get own volunteer profile",
    description="Return the volunteer profile of the currently authenticated user.",
)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Shorthand for GET /volunteer/{uid} using the token UID."""
    fs = _get_firestore()
    uid: str = current_user.get("uid", "")

    volunteer = await fs.get_document(settings.COLLECTION_VOLUNTEERS, uid)
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No volunteer profile found for your account. "
                "Register first using POST /volunteer/register."
            ),
        )
    return _safe_dt(volunteer)


# ─────────────────────────────────────────────────────────────────────────────
# GET /volunteer/{volunteer_id}
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/{volunteer_id}",
    status_code=status.HTTP_200_OK,
    summary="Get a volunteer profile",
    description="Retrieve a single volunteer's full profile by their UID.",
)
async def get_volunteer(
    volunteer_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fetch a single Volunteer document from Firestore by document ID."""
    fs = _get_firestore()

    volunteer = await fs.get_document(settings.COLLECTION_VOLUNTEERS, volunteer_id)
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Volunteer '{volunteer_id}' not found.",
        )
    return _safe_dt(volunteer)


# ─────────────────────────────────────────────────────────────────────────────
# PUT /volunteer/{volunteer_id}
# ─────────────────────────────────────────────────────────────────────────────


@router.put(
    "/{volunteer_id}",
    status_code=status.HTTP_200_OK,
    summary="Update a volunteer profile",
    description=(
        "Update one or more fields on a volunteer profile. "
        "Volunteers can update their own profile; admins can update any profile. "
        "All fields are optional (PATCH semantics despite using PUT)."
    ),
)
async def update_volunteer(
    volunteer_id: str,
    payload: VolunteerUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Partially update a volunteer profile.

    Authorization
    -------------
    - A volunteer may only update their own profile (UID must match).
    - ADMIN and COORDINATOR roles may update any volunteer.
    """
    fs = _get_firestore()
    bq = _get_bigquery()
    uid: str = current_user.get("uid", "")
    role: str = current_user.get("resolved_role", current_user.get("role", "VOLUNTEER"))

    # ── Authorization check ───────────────────────────────────────────
    if uid != volunteer_id and role not in ("ADMIN", "COORDINATOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own volunteer profile.",
        )

    # ── Validate volunteer exists ─────────────────────────────────────
    existing = await fs.get_document(settings.COLLECTION_VOLUNTEERS, volunteer_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Volunteer '{volunteer_id}' not found.",
        )

    # ── Build update payload (only include non-None fields) ───────────
    update_data = payload.model_dump(exclude_none=True)

    if not update_data:
        return {
            "success": True,
            "message": "No fields to update.",
            "volunteer": _safe_dt(existing),
        }

    # Normalise skills to uppercase if provided
    if "skills" in update_data:
        update_data["skills"] = [s.upper() for s in update_data["skills"]]

    update_data["updated_at"] = datetime.utcnow()

    try:
        updated = await fs.update_document(
            settings.COLLECTION_VOLUNTEERS, volunteer_id, update_data
        )
    except Exception as exc:
        logger.error("update_volunteer: Firestore update failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update volunteer profile: {exc}",
        ) from exc

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Volunteer '{volunteer_id}' not found.",
        )

    # Also sync key fields back to the user document
    user_sync: Dict[str, Any] = {}
    for field in ("name", "phone", "location", "fcm_token"):
        if field in update_data:
            user_sync[field] = update_data[field]
    if user_sync:
        try:
            await fs.set_document(
                settings.COLLECTION_USERS, volunteer_id, user_sync, merge=True
            )
        except Exception as exc:
            logger.warning("update_volunteer: user doc sync failed: %s", exc)

    # Log availability change to BigQuery if it was updated
    if "availability" in update_data:
        background_tasks.add_task(
            bq.log_event,
            EventType.VOLUNTEER_AVAILABILITY_CHANGED,
            {
                "user_uid": uid,
                "volunteer_id": volunteer_id,
                "availability": update_data["availability"],
            },
        )

    # Return the merged document
    merged = {**existing, **update_data}
    logger.info(
        "update_volunteer: profile '%s' updated by '%s'. fields=%s",
        volunteer_id,
        uid,
        list(update_data.keys()),
    )

    return {
        "success": True,
        "message": "Volunteer profile updated successfully.",
        "volunteer": _safe_dt(merged),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /volunteer/{volunteer_id}/tasks
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/{volunteer_id}/tasks",
    status_code=status.HTTP_200_OK,
    summary="Get task history for a volunteer",
    description=(
        "Return all tasks (past and present) assigned to a specific volunteer, "
        "ordered newest first. Supports optional status filtering."
    ),
)
async def get_volunteer_tasks(
    volunteer_id: str,
    task_status: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by task status (ASSIGNED, IN_PROGRESS, COMPLETED, etc.).",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Return the task history for a given volunteer.

    Authorization
    -------------
    - Volunteers can only view their own tasks.
    - ADMIN and COORDINATOR roles can view any volunteer's tasks.
    """
    fs = _get_firestore()
    uid: str = current_user.get("uid", "")
    role: str = current_user.get("resolved_role", current_user.get("role", "VOLUNTEER"))

    if uid != volunteer_id and role not in ("ADMIN", "COORDINATOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own task history.",
        )

    # Validate the volunteer exists
    volunteer = await fs.get_document(settings.COLLECTION_VOLUNTEERS, volunteer_id)
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Volunteer '{volunteer_id}' not found.",
        )

    try:
        tasks = await fs.get_tasks_by_volunteer(volunteer_id, limit=limit)
    except Exception as exc:
        logger.error("get_volunteer_tasks: query failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task history.",
        ) from exc

    # Client-side status filter
    if task_status:
        tasks = [t for t in tasks if t.get("status", "").upper() == task_status.upper()]

    # Build quick summary stats
    completed = sum(1 for t in tasks if t.get("status") == "COMPLETED")
    in_progress = sum(1 for t in tasks if t.get("status") == "IN_PROGRESS")
    assigned = sum(1 for t in tasks if t.get("status") == "ASSIGNED")
    cancelled = sum(1 for t in tasks if t.get("status") in ("CANCELLED", "REJECTED"))

    return {
        "volunteer_id": volunteer_id,
        "volunteer_name": volunteer.get("name", ""),
        "tasks": _safe_dt(tasks),
        "total": len(tasks),
        "summary": {
            "completed": completed,
            "in_progress": in_progress,
            "assigned": assigned,
            "cancelled": cancelled,
        },
        "status_filter": task_status,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /volunteer/{volunteer_id}/stats
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/{volunteer_id}/stats",
    status_code=status.HTTP_200_OK,
    summary="Get performance stats for a volunteer",
    description=(
        "Return aggregated performance metrics for a volunteer: "
        "task counts, completion rate, average rating, and skill utilisation."
    ),
)
async def get_volunteer_stats(
    volunteer_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return aggregated performance data for a volunteer."""
    fs = _get_firestore()

    volunteer = await fs.get_document(settings.COLLECTION_VOLUNTEERS, volunteer_id)
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Volunteer '{volunteer_id}' not found.",
        )

    # Fetch all tasks for this volunteer
    try:
        tasks = await fs.get_tasks_by_volunteer(volunteer_id, limit=200)
    except Exception as exc:
        logger.warning("get_volunteer_stats: tasks query failed: %s", exc)
        tasks = []

    total_tasks = len(tasks)
    completed = sum(1 for t in tasks if t.get("status") == "COMPLETED")
    verified = sum(1 for t in tasks if t.get("status") == "VERIFIED")
    cancelled = sum(1 for t in tasks if t.get("status") in ("CANCELLED", "REJECTED"))
    in_progress = sum(1 for t in tasks if t.get("status") == "IN_PROGRESS")

    completion_rate = round(completed / total_tasks, 4) if total_tasks > 0 else 0.0

    # Average actual duration (hours)
    durations = [
        float(t["actual_duration_hours"])
        for t in tasks
        if t.get("actual_duration_hours") is not None
    ]
    avg_duration = round(sum(durations) / len(durations), 2) if durations else None

    # Category breakdown of completed tasks
    category_counts: Dict[str, int] = {}
    for t in tasks:
        if t.get("status") in ("COMPLETED", "VERIFIED"):
            cat = t.get("category", "OTHER")
            category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "volunteer_id": volunteer_id,
        "name": volunteer.get("name", ""),
        "skills": volunteer.get("skills", []),
        "location": volunteer.get("location", ""),
        "availability": volunteer.get("availability", False),
        "status": volunteer.get("status", "AVAILABLE"),
        "rating": volunteer.get("rating"),
        "rating_count": volunteer.get("rating_count", 0),
        "stats": {
            "total_tasks": total_tasks,
            "completed": completed,
            "verified": verified,
            "in_progress": in_progress,
            "cancelled": cancelled,
            "active_tasks": volunteer.get("active_tasks", 0),
            "completion_rate": completion_rate,
            "avg_task_duration_hours": avg_duration,
            "categories_served": category_counts,
        },
        "member_since": _safe_dt(volunteer.get("created_at")),
        "last_active": _safe_dt(volunteer.get("last_active_at")),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /volunteer/{volunteer_id}/availability
# ─────────────────────────────────────────────────────────────────────────────


class AvailabilityToggleRequest(BaseModel):
    availability: bool = Field(
        ..., description="True = available, False = unavailable."
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional reason for availability change.",
    )


@router.patch(
    "/{volunteer_id}/availability",
    status_code=status.HTTP_200_OK,
    summary="Toggle volunteer availability",
    description=(
        "Quickly toggle a volunteer's availability status without updating "
        "other profile fields."
    ),
)
async def toggle_availability(
    volunteer_id: str,
    payload: AvailabilityToggleRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Toggle a volunteer's availability flag."""
    fs = _get_firestore()
    bq = _get_bigquery()
    uid: str = current_user.get("uid", "")
    role: str = current_user.get("resolved_role", current_user.get("role", "VOLUNTEER"))

    if uid != volunteer_id and role not in ("ADMIN", "COORDINATOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own availability.",
        )

    volunteer = await fs.get_document(settings.COLLECTION_VOLUNTEERS, volunteer_id)
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Volunteer '{volunteer_id}' not found.",
        )

    update_data: Dict[str, Any] = {
        "availability": payload.availability,
        "status": "AVAILABLE" if payload.availability else "ON_LEAVE",
        "updated_at": datetime.utcnow(),
    }

    await fs.update_document(settings.COLLECTION_VOLUNTEERS, volunteer_id, update_data)

    background_tasks.add_task(
        bq.log_event,
        EventType.VOLUNTEER_AVAILABILITY_CHANGED,
        {
            "user_uid": uid,
            "volunteer_id": volunteer_id,
            "availability": payload.availability,
            "reason": payload.reason,
        },
    )

    status_label = "available" if payload.availability else "unavailable"
    return {
        "success": True,
        "message": f"Volunteer '{volunteer.get('name')}' is now marked as {status_label}.",
        "volunteer_id": volunteer_id,
        "availability": payload.availability,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /volunteer/{volunteer_id}
# ─────────────────────────────────────────────────────────────────────────────


@router.delete(
    "/{volunteer_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate a volunteer profile",
    description=(
        "Soft-deactivates a volunteer by setting ``availability=False`` and "
        "``status=INACTIVE``. The document is NOT deleted from Firestore "
        "to preserve task history. Requires ADMIN role."
    ),
)
async def deactivate_volunteer(
    volunteer_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Soft-delete (deactivate) a volunteer profile. Requires ADMIN role."""
    fs = _get_firestore()
    role: str = current_user.get("resolved_role", current_user.get("role", "VOLUNTEER"))

    if role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN users can deactivate volunteer profiles.",
        )

    volunteer = await fs.get_document(settings.COLLECTION_VOLUNTEERS, volunteer_id)
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Volunteer '{volunteer_id}' not found.",
        )

    await fs.update_document(
        settings.COLLECTION_VOLUNTEERS,
        volunteer_id,
        {
            "availability": False,
            "status": "INACTIVE",
            "updated_at": datetime.utcnow(),
        },
    )

    return {
        "success": True,
        "message": f"Volunteer '{volunteer.get('name', volunteer_id)}' has been deactivated.",
        "volunteer_id": volunteer_id,
    }
