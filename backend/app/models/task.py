"""
SVAS Backend – Task Models
Pydantic schemas for volunteer tasks linked to community needs.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# ── Enumerations ──────────────────────────────────────────────────────────────


class TaskStatus(str, Enum):
    """Full lifecycle of a volunteer task."""

    PENDING = "PENDING"  # Created, not yet assigned
    ASSIGNED = "ASSIGNED"  # Volunteer matched and notified
    ACCEPTED = "ACCEPTED"  # Volunteer confirmed acceptance
    IN_PROGRESS = "IN_PROGRESS"  # Volunteer actively working
    COMPLETED = "COMPLETED"  # Volunteer marked done
    VERIFIED = "VERIFIED"  # Coordinator verified completion
    CANCELLED = "CANCELLED"  # Cancelled before completion
    REJECTED = "REJECTED"  # Volunteer declined the assignment


class TaskPriority(str, Enum):
    """Task priority – typically inherited from the parent need's urgency."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── Base Schema ───────────────────────────────────────────────────────────────


class TaskBase(BaseModel):
    """Fields shared by all Task schemas."""

    need_id: str = Field(
        ...,
        description="Firestore document ID of the parent Need this task addresses.",
        examples=["need_xyz789"],
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Short, action-oriented title for the task.",
        examples=["Deliver food packets to Ward 7 families"],
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Full description of what the volunteer needs to do.",
    )
    category: str = Field(
        ...,
        description="Category inherited from the parent Need (e.g. FOOD, HEALTH).",
        examples=["FOOD"],
    )
    urgency: str = Field(
        ...,
        description="Urgency level inherited from the parent Need.",
        examples=["HIGH"],
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Task-level priority (can differ from need urgency).",
    )
    location: str = Field(
        ...,
        min_length=2,
        max_length=300,
        description="Human-readable address or area where the task must be performed.",
        examples=["Ward 7, Dharavi, Mumbai, Maharashtra"],
    )
    latitude: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="GPS latitude of the task site.",
    )
    longitude: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="GPS longitude of the task site.",
    )
    assigned_volunteer_id: Optional[str] = Field(
        default=None,
        description="UID of the volunteer assigned to this task.",
    )
    assigned_by: Optional[str] = Field(
        default=None,
        description="UID of the coordinator/admin who made the assignment.",
    )
    required_skills: List[str] = Field(
        default_factory=list,
        description="Skills required to complete this task.",
        examples=[["COOKING", "LOGISTICS"]],
    )
    estimated_duration_hours: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Estimated time in hours to complete the task.",
    )
    due_date: Optional[datetime] = Field(
        default=None,
        description="UTC deadline by which the task must be completed.",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional coordinator notes or instructions.",
    )
    beneficiary_count: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of beneficiaries this specific task serves.",
    )
    is_auto_assigned: bool = Field(
        default=False,
        description="True if the volunteer was matched and assigned by the AI engine.",
    )
    match_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="AI matching score (0–1) used when auto-assigning the volunteer.",
    )


# ── Create Schema ─────────────────────────────────────────────────────────────


class TaskCreate(TaskBase):
    """
    Schema accepted when creating a new task via the API.
    All required fields come from TaskBase.
    Timestamps and IDs are server-generated.
    """

    pass


# ── Update Schema ─────────────────────────────────────────────────────────────


class TaskUpdate(BaseModel):
    """
    Partial-update schema for tasks (PATCH semantics).
    Every field is optional.
    """

    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=2000)
    priority: Optional[TaskPriority] = None
    location: Optional[str] = Field(default=None, min_length=2, max_length=300)
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    assigned_volunteer_id: Optional[str] = None
    assigned_by: Optional[str] = None
    required_skills: Optional[List[str]] = None
    estimated_duration_hours: Optional[float] = Field(default=None, ge=0.0)
    due_date: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    beneficiary_count: Optional[int] = Field(default=None, ge=1)
    status: Optional[TaskStatus] = None
    completion_notes: Optional[str] = Field(default=None, max_length=2000)
    verification_notes: Optional[str] = Field(default=None, max_length=1000)
    actual_duration_hours: Optional[float] = Field(default=None, ge=0.0)
    volunteer_rating: Optional[float] = Field(default=None, ge=1.0, le=5.0)


# ── Status-Transition Payload ─────────────────────────────────────────────────


class TaskStatusUpdate(BaseModel):
    """
    Lightweight payload used specifically to transition a task's status.
    Keeps status-change events separate from general field updates.
    """

    status: TaskStatus = Field(..., description="The new status to transition to.")
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional notes explaining the status change.",
    )
    actual_duration_hours: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Actual hours spent (supplied on COMPLETED status).",
    )
    volunteer_rating: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=5.0,
        description="Coordinator rating for the volunteer (1–5, supplied on VERIFIED status).",
    )


# ── Response Schema ───────────────────────────────────────────────────────────


class TaskResponse(TaskBase):
    """
    Full task record returned by the API, including server-generated metadata.
    """

    id: str = Field(
        ...,
        description="Firestore document ID of this task.",
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current lifecycle status.",
    )
    completion_notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Notes added by the volunteer when marking the task complete.",
    )
    verification_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Notes added by the coordinator during verification.",
    )
    actual_duration_hours: Optional[float] = Field(
        default=None,
        description="Actual time the volunteer spent on this task.",
    )
    volunteer_rating: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=5.0,
        description="Coordinator's rating of the volunteer's performance (1–5).",
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the task was created.",
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp of the last update.",
    )
    assigned_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the volunteer was assigned.",
    )
    accepted_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the volunteer accepted the task.",
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the volunteer started working.",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the volunteer marked the task done.",
    )
    verified_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the coordinator verified completion.",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "task_001",
                "need_id": "need_xyz789",
                "title": "Deliver food packets to Ward 7 families",
                "description": "Collect 200 ration kits from the NGO warehouse and distribute to registered families.",
                "category": "FOOD",
                "urgency": "HIGH",
                "priority": "HIGH",
                "location": "Ward 7, Dharavi, Mumbai",
                "latitude": 19.0453,
                "longitude": 72.8553,
                "assigned_volunteer_id": "uid_volunteer_42",
                "assigned_by": "uid_coordinator_01",
                "required_skills": ["LOGISTICS", "DRIVING"],
                "estimated_duration_hours": 4.0,
                "due_date": "2024-07-16T12:00:00Z",
                "notes": "Carry printed beneficiary list. Contact supervisor on arrival.",
                "beneficiary_count": 200,
                "is_auto_assigned": True,
                "match_score": 0.91,
                "status": "ASSIGNED",
                "completion_notes": None,
                "verification_notes": None,
                "actual_duration_hours": None,
                "volunteer_rating": None,
                "created_at": "2024-07-15T09:00:00Z",
                "updated_at": "2024-07-15T09:05:00Z",
                "assigned_at": "2024-07-15T09:05:00Z",
                "accepted_at": None,
                "started_at": None,
                "completed_at": None,
                "verified_at": None,
            }
        },
    }


# ── List Item Projection ──────────────────────────────────────────────────────


class TaskListItem(BaseModel):
    """
    Minimal projection of a task for list / table views.
    Reduces response payload size.
    """

    id: str
    title: str
    category: str
    urgency: str
    priority: TaskPriority
    status: TaskStatus
    location: str
    assigned_volunteer_id: Optional[str]
    due_date: Optional[datetime]
    beneficiary_count: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Assignment Payload ────────────────────────────────────────────────────────


class TaskAssignRequest(BaseModel):
    """Request body for the manual assignment endpoint."""

    need_id: str = Field(..., description="ID of the need to create a task for.")
    volunteer_id: str = Field(..., description="UID of the volunteer to assign.")
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional instructions from the coordinator.",
    )
    due_date: Optional[datetime] = Field(
        default=None,
        description="Deadline for task completion.",
    )


# ── Completion Payload ────────────────────────────────────────────────────────


class TaskCompleteRequest(BaseModel):
    """Request body submitted by the volunteer when finishing a task."""

    completion_notes: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Summary of what was done and any observations.",
    )
    actual_duration_hours: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="How long the task actually took.",
    )
    photo_urls: List[str] = Field(
        default_factory=list,
        description="URLs to completion proof photos (uploaded to Cloud Storage).",
    )
