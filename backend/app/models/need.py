"""
SVAS Backend – Need Models
Pydantic schemas for community needs submitted to the system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# ── Enumerations ──────────────────────────────────────────────────────────────


class NeedCategory(str, Enum):
    """Top-level category that describes the type of community need."""

    FOOD = "FOOD"
    HEALTH = "HEALTH"
    EDUCATION = "EDUCATION"
    SHELTER = "SHELTER"
    CLOTHING = "CLOTHING"
    OTHER = "OTHER"


class UrgencyLevel(str, Enum):
    """Priority / urgency assigned to a need – either by AI or manually."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NeedStatus(str, Enum):
    """Lifecycle status of a need record."""

    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# ── Base Schema ───────────────────────────────────────────────────────────────


class NeedBase(BaseModel):
    """Fields shared by all Need schemas."""

    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Short, human-readable title for the need.",
        examples=["Emergency food packets needed in Ward 7"],
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Detailed description of the need.",
    )
    category: NeedCategory = Field(
        ...,
        description="Primary category of the need.",
    )
    urgency: UrgencyLevel = Field(
        ...,
        description="Urgency / priority level.",
    )
    location: str = Field(
        ...,
        min_length=2,
        max_length=300,
        description="Human-readable address or area name.",
        examples=["Dharavi, Mumbai, Maharashtra"],
    )
    latitude: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="GPS latitude of the need location.",
    )
    longitude: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="GPS longitude of the need location.",
    )
    reported_by: str = Field(
        ...,
        description="UID of the user / NGO worker who reported this need.",
    )
    beneficiary_count: Optional[int] = Field(
        default=None,
        ge=1,
        description="Estimated number of people affected.",
    )
    key_needs: List[str] = Field(
        default_factory=list,
        description="List of specific items or actions required.",
        examples=[["rice", "lentils", "cooking oil"]],
    )
    recommended_skills: List[str] = Field(
        default_factory=list,
        description="Volunteer skill sets recommended for this need.",
        examples=[["COOKING", "LOGISTICS"]],
    )
    ai_summary: Optional[str] = Field(
        default=None,
        max_length=500,
        description="One-paragraph AI-generated summary of the need.",
    )
    upload_id: Optional[str] = Field(
        default=None,
        description="Reference to the raw upload record that generated this need.",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Free-form tags for search / filtering.",
    )


# ── Create / Input Schema ─────────────────────────────────────────────────────


class NeedCreate(NeedBase):
    """
    Schema accepted when creating a new need via the API.
    All required fields come from NeedBase; nothing extra is needed from the
    caller (timestamps and IDs are server-generated).
    """

    pass


# ── Update Schema ─────────────────────────────────────────────────────────────


class NeedUpdate(BaseModel):
    """
    Partial-update schema – every field is optional so callers can PATCH
    only the attributes they want to change.
    """

    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[NeedCategory] = None
    urgency: Optional[UrgencyLevel] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    beneficiary_count: Optional[int] = None
    key_needs: Optional[List[str]] = None
    recommended_skills: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[NeedStatus] = None


# ── Response Schema ───────────────────────────────────────────────────────────


class NeedResponse(NeedBase):
    """
    Full need record returned by the API, including server-generated fields.
    """

    id: str = Field(
        ...,
        description="Firestore document ID.",
    )
    status: NeedStatus = Field(
        default=NeedStatus.OPEN,
        description="Current lifecycle status of this need.",
    )
    assigned_volunteer_ids: List[str] = Field(
        default_factory=list,
        description="UIDs of volunteers currently assigned to work on this need.",
    )
    task_ids: List[str] = Field(
        default_factory=list,
        description="IDs of tasks created for this need.",
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the need was first recorded.",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the last update.",
    )
    resolved_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the need was marked resolved.",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "abc123",
                "title": "Emergency food packets needed in Ward 7",
                "description": "Approximately 200 families displaced by flooding require immediate food assistance.",
                "category": "FOOD",
                "urgency": "HIGH",
                "location": "Ward 7, Dharavi, Mumbai",
                "latitude": 19.0453,
                "longitude": 72.8553,
                "reported_by": "uid_ngo_worker_001",
                "beneficiary_count": 200,
                "key_needs": ["rice", "lentils", "cooking oil", "drinking water"],
                "recommended_skills": ["COOKING", "LOGISTICS", "DRIVING"],
                "ai_summary": "Two hundred flood-displaced families in Ward 7 urgently need dry food rations and clean water.",
                "status": "OPEN",
                "assigned_volunteer_ids": [],
                "task_ids": [],
                "tags": ["flood", "relief", "mumbai"],
                "upload_id": None,
                "created_at": "2024-07-15T08:30:00Z",
                "updated_at": None,
                "resolved_at": None,
            }
        },
    }


# ── Lightweight List Item ─────────────────────────────────────────────────────


class NeedListItem(BaseModel):
    """
    Minimal projection of a need used in list / table views to reduce payload size.
    """

    id: str
    title: str
    category: NeedCategory
    urgency: UrgencyLevel
    status: NeedStatus
    location: str
    latitude: Optional[float]
    longitude: Optional[float]
    beneficiary_count: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AI Analysis Result ────────────────────────────────────────────────────────


class NeedAnalysisResult(BaseModel):
    """
    Structured output returned by the Gemini AI analysis endpoint.
    Mirrors the JSON schema that the LLM prompt instructs the model to produce.
    """

    category: NeedCategory = Field(..., description="Detected primary category.")
    urgency: UrgencyLevel = Field(..., description="Detected urgency level.")
    summary: str = Field(..., description="1–2 sentence summary of the need.")
    key_needs: List[str] = Field(
        default_factory=list, description="Specific items or actions required."
    )
    estimated_beneficiaries: Optional[int] = Field(
        default=None, description="Estimated number of people affected."
    )
    recommended_skills: List[str] = Field(
        default_factory=list, description="Volunteer skill sets recommended."
    )
    location_hints: Optional[str] = Field(
        default=None, description="Any location information mentioned in the text."
    )
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Model confidence score (0–1)."
    )
    raw_model_output: Optional[str] = Field(
        default=None, description="Raw string returned by the model (for debugging)."
    )
