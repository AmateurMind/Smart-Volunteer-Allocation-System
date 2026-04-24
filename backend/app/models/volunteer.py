"""
SVAS Backend – Volunteer Models
Pydantic schemas for volunteer profiles, skills, and availability.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# ── Enumerations ──────────────────────────────────────────────────────────────


class SkillSet(str, Enum):
    """Skills a volunteer can possess, used for matching against needs."""

    MEDICAL = "MEDICAL"
    EDUCATION = "EDUCATION"
    LOGISTICS = "LOGISTICS"
    COUNSELING = "COUNSELING"
    DRIVING = "DRIVING"
    COOKING = "COOKING"
    GENERAL = "GENERAL"


class VolunteerStatus(str, Enum):
    """Current operational status of a volunteer."""

    AVAILABLE = "AVAILABLE"
    ON_ASSIGNMENT = "ON_ASSIGNMENT"
    ON_LEAVE = "ON_LEAVE"
    INACTIVE = "INACTIVE"


# ── Base Schema ───────────────────────────────────────────────────────────────


class VolunteerBase(BaseModel):
    """Fields shared across all volunteer schemas."""

    uid: str = Field(
        ...,
        description="Firebase UID – must match the authenticated user record.",
        examples=["uid_vol_abc123"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Full display name of the volunteer.",
        examples=["Rahul Mehta"],
    )
    email: str = Field(
        ...,
        description="Contact e-mail address.",
        examples=["rahul.mehta@email.com"],
    )
    phone: str = Field(
        ...,
        pattern=r"^\+?[0-9\s\-]{7,20}$",
        description="Contact phone number (E.164 preferred).",
        examples=["+91 98765 43210"],
    )
    skills: List[SkillSet] = Field(
        default_factory=list,
        description="List of skill categories this volunteer has.",
        examples=[["MEDICAL", "DRIVING"]],
    )
    location: str = Field(
        ...,
        min_length=2,
        max_length=300,
        description="City / district / area the volunteer is based in.",
        examples=["Pune, Maharashtra"],
    )
    latitude: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="GPS latitude of the volunteer's base location.",
    )
    longitude: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="GPS longitude of the volunteer's base location.",
    )
    availability: bool = Field(
        default=True,
        description="Whether the volunteer is currently available for assignments.",
    )
    languages: List[str] = Field(
        default_factory=list,
        description="Languages spoken by the volunteer.",
        examples=[["Hindi", "Marathi", "English"]],
    )
    bio: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Short description or background of the volunteer.",
    )
    profile_image_url: Optional[str] = Field(
        default=None,
        description="Public URL to the volunteer's profile photo.",
    )
    fcm_token: Optional[str] = Field(
        default=None,
        description="Firebase Cloud Messaging device token for push notifications.",
    )
    max_active_tasks: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum number of tasks the volunteer can handle simultaneously.",
    )

    model_config = {"use_enum_values": True}


# ── Create / Input Schema ─────────────────────────────────────────────────────


class VolunteerCreate(VolunteerBase):
    """
    Payload accepted when a user registers as a volunteer.
    All required fields come from VolunteerBase; server generates
    timestamps, ratings, and task counters automatically.
    """

    pass


# ── Update Schema ─────────────────────────────────────────────────────────────


class VolunteerUpdate(BaseModel):
    """
    Partial-update schema – every field is optional so callers can
    PATCH only the attributes they need to change.
    """

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, pattern=r"^\+?[0-9\s\-]{7,20}$")
    skills: Optional[List[SkillSet]] = None
    location: Optional[str] = Field(default=None, max_length=300)
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    availability: Optional[bool] = None
    languages: Optional[List[str]] = None
    bio: Optional[str] = Field(default=None, max_length=500)
    profile_image_url: Optional[str] = None
    fcm_token: Optional[str] = None
    max_active_tasks: Optional[int] = Field(default=None, ge=1, le=20)
    status: Optional[VolunteerStatus] = None


# ── Response Schema ───────────────────────────────────────────────────────────


class VolunteerResponse(VolunteerBase):
    """
    Full volunteer record returned by the API, including server-generated
    performance and assignment metadata.
    """

    id: str = Field(
        ...,
        description="Firestore document ID (usually same as uid).",
    )
    status: VolunteerStatus = Field(
        default=VolunteerStatus.AVAILABLE,
        description="Current operational status of the volunteer.",
    )
    tasks_completed: int = Field(
        default=0,
        ge=0,
        description="Total number of tasks successfully completed.",
    )
    active_tasks: int = Field(
        default=0,
        ge=0,
        description="Number of tasks currently in progress.",
    )
    rating: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Average rating given by coordinators (0–5 stars).",
    )
    rating_count: int = Field(
        default=0,
        ge=0,
        description="Number of ratings received.",
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the volunteer profile was created.",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the last profile update.",
    )
    last_active_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the volunteer's last activity.",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "uid_vol_abc123",
                "uid": "uid_vol_abc123",
                "name": "Rahul Mehta",
                "email": "rahul.mehta@email.com",
                "phone": "+91 98765 43210",
                "skills": ["MEDICAL", "DRIVING"],
                "location": "Pune, Maharashtra",
                "latitude": 18.5204,
                "longitude": 73.8567,
                "availability": True,
                "languages": ["Hindi", "Marathi", "English"],
                "bio": "Certified first-aid responder with 3 years NGO experience.",
                "profile_image_url": None,
                "fcm_token": None,
                "max_active_tasks": 3,
                "status": "AVAILABLE",
                "tasks_completed": 14,
                "active_tasks": 1,
                "rating": 4.7,
                "rating_count": 11,
                "created_at": "2024-03-10T10:00:00Z",
                "updated_at": "2024-07-12T15:30:00Z",
                "last_active_at": "2024-07-14T09:00:00Z",
            }
        },
    }


# ── Lightweight List Item ─────────────────────────────────────────────────────


class VolunteerListItem(BaseModel):
    """
    Minimal projection used in list / table views to reduce payload size.
    """

    id: str
    name: str
    location: str
    skills: List[str]
    availability: bool
    status: VolunteerStatus
    active_tasks: int
    tasks_completed: int
    rating: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Match Result ──────────────────────────────────────────────────────────────


class VolunteerMatchResult(BaseModel):
    """
    Volunteer record enriched with matching metadata, returned by
    the /match endpoint when finding best volunteers for a need.
    """

    volunteer: VolunteerResponse = Field(..., description="Full volunteer profile.")
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite match score (0 = worst, 1 = best).",
    )
    rank: int = Field(
        ...,
        ge=1,
        description="Position in the ranked result list (1 = best match).",
    )
    distance_km: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Straight-line distance from volunteer to need location (km).",
    )
    skill_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Skill-match component of the composite score.",
    )
    distance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Distance-proximity component of the composite score.",
    )
    workload_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Workload-availability component of the composite score.",
    )
    match_reasons: List[str] = Field(
        default_factory=list,
        description="Human-readable reasons why this volunteer was selected.",
        examples=[
            [
                "Has MEDICAL skill required by this need",
                "Located 4.2 km from the need site",
                "Currently has 0 active tasks",
            ]
        ],
    )
    ai_explanation: Optional[str] = Field(
        default=None,
        description="AI-generated narrative explaining the match (optional).",
    )


# ── Volunteer Rating Request ──────────────────────────────────────────────────


class VolunteerRatingRequest(BaseModel):
    """Payload for submitting a rating after a task is completed."""

    volunteer_id: str = Field(..., description="ID of the volunteer being rated.")
    task_id: str = Field(..., description="ID of the completed task.")
    rating: float = Field(..., ge=1.0, le=5.0, description="Star rating (1–5).")
    feedback: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional written feedback from the coordinator.",
    )
