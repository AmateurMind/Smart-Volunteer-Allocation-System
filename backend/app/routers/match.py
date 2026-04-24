"""
SVAS Backend – /match Router
Smart volunteer matching and task assignment endpoints.
Uses MatchingService (Haversine + weighted scoring) to rank volunteers against
a community need and handles both manual and automatic assignments.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.middleware.auth import get_current_user
from app.services.bigquery_service import BigQueryService, EventType
from app.services.fcm_service import FCMService
from app.services.firestore_service import FirestoreService
from app.services.gemini_service import GeminiService
from app.services.matching_service import MatchingService
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/match", tags=["Matching & Assignment"])

# ── Service singletons ────────────────────────────────────────────────────────

_firestore: Optional[FirestoreService] = None
_matching: Optional[MatchingService] = None
_gemini: Optional[GeminiService] = None
_fcm: Optional[FCMService] = None
_bigquery: Optional[BigQueryService] = None


def _get_firestore() -> FirestoreService:
    global _firestore
    if _firestore is None:
        _firestore = FirestoreService()
    return _firestore


def _get_matching() -> MatchingService:
    global _matching
    if _matching is None:
        _matching = MatchingService()
    return _matching


def _get_gemini() -> GeminiService:
    global _gemini
    if _gemini is None:
        _gemini = GeminiService()
    return _gemini


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


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ─────────────────────────────────────────────────────────────────────────────


class MatchRequest(BaseModel):
    """Request body for the volunteer matching endpoint."""

    need_id: str = Field(
        ...,
        description="Firestore document ID of the need to match volunteers against.",
        examples=["need_abc123"],
    )
    top_n: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of volunteer matches to return.",
    )
    max_distance_km: Optional[float] = Field(
        default=None,
        ge=0.0,
        description=(
            "Maximum volunteer-to-need distance in km. "
            "Defaults to the system setting (50 km). Set 0 for unlimited."
        ),
    )
    include_ai_explanation: bool = Field(
        default=False,
        description=(
            "If True, each match result includes a Gemini-generated narrative "
            "explaining why the volunteer was selected. Adds latency."
        ),
    )


class AssignRequest(BaseModel):
    """Request body for the manual assignment endpoint."""

    need_id: str = Field(
        ...,
        description="Firestore document ID of the need to assign.",
    )
    volunteer_id: str = Field(
        ...,
        description="Firestore document ID (UID) of the volunteer to assign.",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional coordinator instructions for the volunteer.",
    )
    due_date: Optional[datetime] = Field(
        default=None,
        description="Optional UTC deadline for the task.",
    )
    send_notification: bool = Field(
        default=True,
        description="If True, send an FCM push notification to the volunteer.",
    )


class MatchResultItem(BaseModel):
    """A single ranked volunteer result."""

    rank: int
    volunteer_id: str
    name: str
    location: str
    skills: List[str]
    availability: bool
    active_tasks: int
    tasks_completed: int
    rating: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]
    score: float
    distance_km: Optional[float]
    skill_score: float
    distance_score: float
    workload_score: float
    match_reasons: List[str]
    ai_explanation: Optional[str] = None


class MatchResponse(BaseModel):
    """Response from the volunteer matching endpoint."""

    need_id: str
    need_title: str
    need_category: str
    need_urgency: str
    need_location: str
    total_volunteers_evaluated: int
    matches: List[MatchResultItem]
    message: str


class AssignResponse(BaseModel):
    """Response from the assignment endpoint."""

    success: bool
    task_id: str
    need_id: str
    volunteer_id: str
    message: str
    task: Dict[str, Any]


class TaskStatusUpdateRequest(BaseModel):
    """Request body for updating a task's status."""

    status: str = Field(
        ...,
        description="New status: ACCEPTED | IN_PROGRESS | COMPLETED | CANCELLED | REJECTED",
        examples=["COMPLETED"],
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Notes explaining the status change.",
    )
    actual_duration_hours: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Actual hours spent (for COMPLETED status).",
    )
    volunteer_rating: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=5.0,
        description="Coordinator rating (for VERIFIED status).",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_VALID_STATUSES = {
    "ACCEPTED",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
    "REJECTED",
    "VERIFIED",
    "PENDING",
    "ASSIGNED",
}


def _safe_dt(data: Any) -> Any:
    """Recursively convert datetime objects to ISO strings for JSON serialisation."""
    if isinstance(data, dict):
        return {k: _safe_dt(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_safe_dt(v) for v in data]
    if isinstance(data, datetime):
        return data.isoformat()
    return data


async def _build_task_document(
    need: Dict[str, Any],
    volunteer_id: str,
    assigned_by: str,
    notes: Optional[str] = None,
    due_date: Optional[datetime] = None,
    match_score: Optional[float] = None,
    match_reasons: Optional[List[str]] = None,
    is_auto: bool = False,
) -> Dict[str, Any]:
    """
    Construct a Task Firestore document from a need and a volunteer assignment.
    """
    now = datetime.utcnow()
    return {
        "need_id": need.get("id", ""),
        "title": need.get("title", "Volunteer Task"),
        "description": need.get("description", ""),
        "category": need.get("category", "OTHER"),
        "urgency": need.get("urgency", "MEDIUM"),
        "priority": need.get("urgency", "MEDIUM"),
        "location": need.get("location", ""),
        "latitude": need.get("latitude"),
        "longitude": need.get("longitude"),
        "assigned_volunteer_id": volunteer_id,
        "assigned_by": assigned_by,
        "required_skills": need.get("recommended_skills", []),
        "beneficiary_count": need.get("beneficiary_count"),
        "notes": notes,
        "due_date": due_date,
        "status": "ASSIGNED",
        "is_auto_assigned": is_auto,
        "match_score": match_score,
        "match_reasons": match_reasons or [],
        "assigned_at": now,
        "created_at": now,
        "updated_at": now,
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /match  – Find best volunteers
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=MatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Find best volunteers for a need",
    description=(
        "Runs the SVAS smart matching algorithm against all available volunteers "
        "and returns a ranked list of the best candidates for a given community need. "
        "Scores are computed using a weighted combination of skill alignment, "
        "geographic proximity, availability, and current workload."
    ),
)
async def match_volunteers(
    request: MatchRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> MatchResponse:
    """
    Find and rank the best available volunteers for a specific need.

    Algorithm weights (configurable via settings):
    - Skill match  : 40 %
    - Distance     : 30 %
    - Availability : 20 %
    - Workload     : 10 %
    """
    fs = _get_firestore()
    matching = _get_matching()
    gemini = _get_gemini()
    bq = _get_bigquery()
    user_uid: str = current_user.get("uid", "anonymous")

    # ── 1. Fetch the need ─────────────────────────────────────────────
    need = await fs.get_document(settings.COLLECTION_NEEDS, request.need_id)
    if not need:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Need '{request.need_id}' not found.",
        )

    # ── 2. Fetch all available volunteers ─────────────────────────────
    volunteers = await fs.get_available_volunteers(limit=200)

    # ── 3. Run matching algorithm ─────────────────────────────────────
    if request.max_distance_km is not None:
        matching._max_dist = request.max_distance_km or 999_999  # 0 = unlimited

    raw_matches = await matching.find_best_volunteers(
        need, volunteers, top_n=request.top_n
    )

    # ── 4. Optionally generate AI explanations ────────────────────────
    if request.include_ai_explanation and raw_matches:
        for match in raw_matches:
            try:
                explanation = await gemini.generate_match_explanation(match, need)
                match["ai_explanation"] = explanation
            except Exception as exc:
                logger.warning(
                    "AI explanation failed for volunteer %s: %s", match.get("id"), exc
                )
                match["ai_explanation"] = None

    # ── 5. Serialize matches into response schema ─────────────────────
    match_items: List[MatchResultItem] = []
    for m in raw_matches:
        match_items.append(
            MatchResultItem(
                rank=m.get("rank", 0),
                volunteer_id=m.get("id") or m.get("uid", ""),
                name=m.get("name", "Unknown"),
                location=m.get("location", ""),
                skills=m.get("skills", []),
                availability=m.get("availability", False),
                active_tasks=m.get("active_tasks", 0),
                tasks_completed=m.get("tasks_completed", 0),
                rating=m.get("rating"),
                latitude=m.get("latitude"),
                longitude=m.get("longitude"),
                score=m.get("score", 0.0),
                distance_km=m.get("distance_km"),
                skill_score=m.get("skill_score", 0.0),
                distance_score=m.get("distance_score", 0.0),
                workload_score=m.get("workload_score", 0.0),
                match_reasons=m.get("match_reasons", []),
                ai_explanation=m.get("ai_explanation"),
            )
        )

    # ── 6. Log event in background ────────────────────────────────────
    background_tasks.add_task(
        bq.log_event,
        EventType.MATCH_REQUESTED,
        {
            "user_uid": user_uid,
            "need_id": request.need_id,
            "category": need.get("category"),
            "urgency": need.get("urgency"),
            "volunteers_evaluated": len(volunteers),
            "matches_returned": len(match_items),
        },
    )

    return MatchResponse(
        need_id=request.need_id,
        need_title=need.get("title", ""),
        need_category=need.get("category", "OTHER"),
        need_urgency=need.get("urgency", "MEDIUM"),
        need_location=need.get("location", ""),
        total_volunteers_evaluated=len(volunteers),
        matches=match_items,
        message=(
            f"Found {len(match_items)} volunteer match(es) from a pool of "
            f"{len(volunteers)} available volunteer(s)."
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /match/assign  – Manual assignment
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/assign",
    response_model=AssignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually assign a volunteer to a need",
    description=(
        "Create a Task document linking a specific volunteer to a community need. "
        "Updates the need's status to ASSIGNED, increments the volunteer's "
        "active_tasks counter, and optionally sends an FCM push notification."
    ),
)
async def assign_volunteer(
    request: AssignRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> AssignResponse:
    """
    Manually assign a volunteer to a need.

    Steps
    -----
    1. Validate the need and volunteer exist.
    2. Check the volunteer is available and not at capacity.
    3. Create a Task document.
    4. Update the need status → ASSIGNED.
    5. Increment volunteer active_tasks.
    6. Send FCM notification (optional).
    7. Log to BigQuery.
    """
    fs = _get_firestore()
    fcm = _get_fcm()
    bq = _get_bigquery()
    user_uid: str = current_user.get("uid", "anonymous")

    # ── 1. Validate need ──────────────────────────────────────────────
    need = await fs.get_document(settings.COLLECTION_NEEDS, request.need_id)
    if not need:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Need '{request.need_id}' not found.",
        )

    if need.get("status") in ("RESOLVED", "CLOSED"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Need '{request.need_id}' is already {need.get('status')} and cannot be assigned.",
        )

    # ── 2. Validate volunteer ─────────────────────────────────────────
    volunteer = await fs.get_document(
        settings.COLLECTION_VOLUNTEERS, request.volunteer_id
    )
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Volunteer '{request.volunteer_id}' not found.",
        )

    if not volunteer.get("availability", True):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Volunteer '{volunteer.get('name', request.volunteer_id)}' "
                "is currently marked as unavailable."
            ),
        )

    active = int(volunteer.get("active_tasks", 0))
    max_active = int(volunteer.get("max_active_tasks", 3))
    if active >= max_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Volunteer '{volunteer.get('name')}' is at capacity "
                f"({active}/{max_active} active tasks). "
                "Please choose a different volunteer."
            ),
        )

    # ── 3. Create Task document ───────────────────────────────────────
    task_data = await _build_task_document(
        need=need,
        volunteer_id=request.volunteer_id,
        assigned_by=user_uid,
        notes=request.notes,
        due_date=request.due_date,
        is_auto=False,
    )

    task_id = await fs.create_document(settings.COLLECTION_TASKS, task_data)
    task_data["id"] = task_id

    # ── 4 & 5. Update need + volunteer concurrently ───────────────────
    import asyncio

    now = datetime.utcnow()

    # Get current assigned list and append new volunteer
    current_assigned = need.get("assigned_volunteer_ids", [])
    if request.volunteer_id not in current_assigned:
        current_assigned.append(request.volunteer_id)

    current_tasks = need.get("task_ids", [])
    if task_id not in current_tasks:
        current_tasks.append(task_id)

    await asyncio.gather(
        fs.update_document(
            settings.COLLECTION_NEEDS,
            request.need_id,
            {
                "status": "ASSIGNED",
                "assigned_volunteer_ids": current_assigned,
                "task_ids": current_tasks,
                "updated_at": now,
            },
        ),
        fs.increment_volunteer_active_tasks(request.volunteer_id, delta=1),
    )

    # ── 6. FCM notification (background) ─────────────────────────────
    if request.send_notification:
        vol_token = volunteer.get("fcm_token")
        if vol_token:
            background_tasks.add_task(
                fcm.send_task_assignment,
                volunteer_token=vol_token,
                task=task_data,
            )

    # ── 7. BigQuery logging (background) ─────────────────────────────
    background_tasks.add_task(
        bq.log_event,
        EventType.TASK_ASSIGNED,
        {
            "user_uid": user_uid,
            "need_id": request.need_id,
            "task_id": task_id,
            "volunteer_id": request.volunteer_id,
            "category": need.get("category"),
            "urgency": need.get("urgency"),
            "location": need.get("location"),
        },
    )

    logger.info(
        "Manual assignment: task '%s' created, volunteer '%s' assigned to need '%s'.",
        task_id,
        request.volunteer_id,
        request.need_id,
    )

    return AssignResponse(
        success=True,
        task_id=task_id,
        need_id=request.need_id,
        volunteer_id=request.volunteer_id,
        message=(
            f"Volunteer '{volunteer.get('name', request.volunteer_id)}' "
            f"successfully assigned to '{need.get('title', request.need_id)}'."
        ),
        task=_safe_dt(task_data),
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /match/auto-assign/{need_id}  – Automatic assignment
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/auto-assign/{need_id}",
    response_model=AssignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Auto-assign the best volunteer to a need",
    description=(
        "Let the SVAS AI engine automatically select and assign the highest-scoring "
        "available volunteer for the given need. "
        "Creates a Task, updates the Need status, and sends an FCM notification."
    ),
)
async def auto_assign(
    need_id: str,
    background_tasks: BackgroundTasks,
    send_notification: bool = True,
    current_user: dict = Depends(get_current_user),
) -> AssignResponse:
    """
    Automatically select and assign the best available volunteer to a need.

    Delegates to ``MatchingService.auto_assign()`` which handles the full
    matching, Firestore updates, and task creation flow.
    """
    fs = _get_firestore()
    matching = _get_matching()
    fcm = _get_fcm()
    bq = _get_bigquery()
    user_uid: str = current_user.get("uid", "anonymous")

    # Validate need exists first for a cleaner error message
    need = await fs.get_document(settings.COLLECTION_NEEDS, need_id)
    if not need:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Need '{need_id}' not found.",
        )

    if need.get("status") in ("RESOLVED", "CLOSED"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Need '{need_id}' is {need.get('status')} and cannot be auto-assigned.",
        )

    # Log the trigger event
    background_tasks.add_task(
        bq.log_event,
        EventType.AUTO_ASSIGN_TRIGGERED,
        {
            "user_uid": user_uid,
            "need_id": need_id,
            "category": need.get("category"),
            "urgency": need.get("urgency"),
        },
    )

    # Run auto-assignment
    task = await matching.auto_assign(need_id, fs)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No suitable volunteer found for this need. "
                "All volunteers may be unavailable, at capacity, "
                "or lack the required skills."
            ),
        )

    task_id: str = task.get("id", "")
    volunteer_id: str = task.get("assigned_volunteer_id", "")

    # Fetch volunteer name for the response message
    volunteer = await fs.get_document(settings.COLLECTION_VOLUNTEERS, volunteer_id)
    vol_name = volunteer.get("name", volunteer_id) if volunteer else volunteer_id

    # FCM notification (background)
    if send_notification and volunteer:
        vol_token = volunteer.get("fcm_token")
        if vol_token:
            background_tasks.add_task(
                fcm.send_task_assignment,
                volunteer_token=vol_token,
                task=task,
            )

    # BigQuery log
    background_tasks.add_task(
        bq.log_event,
        EventType.TASK_ASSIGNED,
        {
            "user_uid": user_uid,
            "need_id": need_id,
            "task_id": task_id,
            "volunteer_id": volunteer_id,
            "category": need.get("category"),
            "urgency": need.get("urgency"),
            "location": need.get("location"),
            "match_score": task.get("match_score"),
            "is_auto": True,
        },
    )

    logger.info(
        "Auto-assign: task '%s' created, volunteer '%s' assigned to need '%s' (score=%.3f).",
        task_id,
        volunteer_id,
        need_id,
        task.get("match_score", 0),
    )

    return AssignResponse(
        success=True,
        task_id=task_id,
        need_id=need_id,
        volunteer_id=volunteer_id,
        message=(
            f"Auto-assigned '{vol_name}' to '{need.get('title', need_id)}' "
            f"(match score: {task.get('match_score', 0):.0%})."
        ),
        task=_safe_dt(task),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /match/tasks  – List all tasks
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/tasks",
    status_code=status.HTTP_200_OK,
    summary="List tasks with optional status filter",
    description="Return task documents from Firestore with optional status filtering.",
)
async def list_tasks(
    task_status: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by task status (PENDING, ASSIGNED, IN_PROGRESS, COMPLETED, etc.)",
    ),
    volunteer_id: Optional[str] = Query(
        default=None,
        description="Filter by assigned volunteer ID.",
    ),
    need_id: Optional[str] = Query(
        default=None,
        description="Filter by parent need ID.",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return a filtered list of task documents."""
    fs = _get_firestore()

    if volunteer_id:
        tasks = await fs.get_tasks_by_volunteer(volunteer_id, limit=limit)
    elif need_id:
        tasks = await fs.get_tasks_by_need(need_id, limit=limit)
    elif task_status:
        tasks = await fs.get_tasks_by_status(task_status.upper(), limit=limit)
    else:
        tasks = await fs.query_collection(
            settings.COLLECTION_TASKS,
            order_by="created_at",
            descending=True,
            limit=limit,
        )

    return {
        "total": len(tasks),
        "tasks": _safe_dt(tasks),
        "filters": {
            "status": task_status,
            "volunteer_id": volunteer_id,
            "need_id": need_id,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /match/tasks/{task_id}  – Get single task
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/tasks/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="Get a specific task record",
)
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fetch a single Task document by its Firestore ID."""
    fs = _get_firestore()
    task = await fs.get_document(settings.COLLECTION_TASKS, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )
    return _safe_dt(task)


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /match/tasks/{task_id}/status  – Update task status
# ─────────────────────────────────────────────────────────────────────────────


@router.patch(
    "/tasks/{task_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Update a task's lifecycle status",
    description=(
        "Transition a task to a new lifecycle status. "
        "Triggers volunteer counter updates and coordinator notifications where appropriate."
    ),
)
async def update_task_status(
    task_id: str,
    request: TaskStatusUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Transition a task's status and trigger appropriate side-effects.

    Side-effects by transition
    --------------------------
    - → COMPLETED  : decrement active_tasks, increment tasks_completed on volunteer.
    - → CANCELLED  : decrement active_tasks on volunteer.
    - → REJECTED   : decrement active_tasks on volunteer; reopen the parent need.
    """
    fs = _get_firestore()
    bq = _get_bigquery()
    user_uid: str = current_user.get("uid", "anonymous")

    new_status = request.status.upper()
    if new_status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{request.status}'. Valid values: {sorted(_VALID_STATUSES)}",
        )

    # Fetch the task
    task = await fs.get_document(settings.COLLECTION_TASKS, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    now = datetime.utcnow()
    update_data: Dict[str, Any] = {
        "status": new_status,
        "updated_at": now,
    }

    # Status-specific fields
    if new_status == "ACCEPTED":
        update_data["accepted_at"] = now
    elif new_status == "IN_PROGRESS":
        update_data["started_at"] = now
    elif new_status == "COMPLETED":
        update_data["completed_at"] = now
        if request.notes:
            update_data["completion_notes"] = request.notes
        if request.actual_duration_hours is not None:
            update_data["actual_duration_hours"] = request.actual_duration_hours
    elif new_status == "VERIFIED":
        update_data["verified_at"] = now
        if request.volunteer_rating is not None:
            update_data["volunteer_rating"] = request.volunteer_rating
        if request.notes:
            update_data["verification_notes"] = request.notes
    elif new_status in ("CANCELLED", "REJECTED"):
        if request.notes:
            update_data["completion_notes"] = request.notes

    # Persist the status change
    await fs.update_document(settings.COLLECTION_TASKS, task_id, update_data)

    # ── Side-effects ──────────────────────────────────────────────────
    volunteer_id = task.get("assigned_volunteer_id")
    need_id = task.get("need_id")

    if volunteer_id:
        if new_status == "COMPLETED":
            background_tasks.add_task(
                fs.increment_volunteer_completed_tasks, volunteer_id
            )
            # Update rating if supplied
            if request.volunteer_rating is not None:
                background_tasks.add_task(
                    _update_volunteer_rating,
                    fs,
                    volunteer_id,
                    request.volunteer_rating,
                )
        elif new_status in ("CANCELLED", "REJECTED"):
            background_tasks.add_task(
                fs.increment_volunteer_active_tasks, volunteer_id, -1
            )
            # Reopen the need if rejected so it can be reassigned
            if new_status == "REJECTED" and need_id:
                background_tasks.add_task(
                    fs.update_document,
                    settings.COLLECTION_NEEDS,
                    need_id,
                    {"status": "OPEN", "updated_at": now},
                )

    # BigQuery log
    event_map = {
        "ACCEPTED": EventType.TASK_ACCEPTED,
        "IN_PROGRESS": EventType.TASK_STARTED,
        "COMPLETED": EventType.TASK_COMPLETED,
        "CANCELLED": EventType.TASK_CANCELLED,
    }
    bq_event_type = event_map.get(new_status, EventType.TASK_ASSIGNED)
    background_tasks.add_task(
        bq.log_event,
        bq_event_type,
        {
            "user_uid": user_uid,
            "task_id": task_id,
            "need_id": need_id,
            "volunteer_id": volunteer_id,
            "category": task.get("category"),
            "urgency": task.get("urgency"),
        },
    )

    task.update(update_data)
    return {
        "success": True,
        "task_id": task_id,
        "new_status": new_status,
        "message": f"Task status updated to '{new_status}'.",
        "task": _safe_dt(task),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Private async helpers
# ─────────────────────────────────────────────────────────────────────────────


async def _update_volunteer_rating(
    fs: FirestoreService,
    volunteer_id: str,
    new_rating: float,
) -> None:
    """
    Recalculate and persist the volunteer's average rating after a new rating
    is submitted.  Uses the existing ``rating`` and ``rating_count`` fields
    stored in Firestore to compute a running average.
    """
    try:
        volunteer = await fs.get_document(settings.COLLECTION_VOLUNTEERS, volunteer_id)
        if not volunteer:
            return

        existing_rating = float(volunteer.get("rating") or 0.0)
        existing_count = int(volunteer.get("rating_count") or 0)

        new_count = existing_count + 1
        # Running average formula: (old_avg * old_count + new_value) / new_count
        updated_avg = round(
            (existing_rating * existing_count + new_rating) / new_count, 2
        )

        await fs.update_document(
            settings.COLLECTION_VOLUNTEERS,
            volunteer_id,
            {
                "rating": updated_avg,
                "rating_count": new_count,
                "updated_at": datetime.utcnow(),
            },
        )
        logger.debug(
            "Updated volunteer '%s' rating: %.2f → %.2f (n=%d)",
            volunteer_id,
            existing_rating,
            updated_avg,
            new_count,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to update volunteer rating: %s", exc)
