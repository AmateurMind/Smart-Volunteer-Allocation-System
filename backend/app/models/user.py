"""
SVAS – User Pydantic Models
Covers authentication roles, profile data, and API request/response shapes.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────


class UserRole(str, Enum):
    """Platform roles that drive access-control logic."""

    ADMIN = "ADMIN"
    COORDINATOR = "COORDINATOR"
    VOLUNTEER = "VOLUNTEER"


# ─────────────────────────────────────────────────────────────────────────────
# Base / Shared fields
# ─────────────────────────────────────────────────────────────────────────────


class UserBase(BaseModel):
    """Fields shared across create, update, and response models."""

    uid: str = Field(
        ...,
        description="Firebase UID – primary identifier across all services.",
        examples=["uid_abc123XYZ"],
    )
    email: str = Field(
        ...,
        description="User e-mail address (verified by Firebase Auth).",
        examples=["coordinator@ngo.org"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Full display name.",
        examples=["Priya Sharma"],
    )
    role: UserRole = Field(
        default=UserRole.VOLUNTEER,
        description="Platform role that determines access level.",
    )
    phone: Optional[str] = Field(
        default=None,
        pattern=r"^\+?[0-9\s\-]{7,20}$",
        description="Contact phone number (E.164 preferred).",
        examples=["+91 98765 43210"],
    )
    profile_image_url: Optional[str] = Field(
        default=None,
        description="Public URL to the user's profile photo.",
    )
    bio: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Short bio or introduction.",
    )
    location: Optional[str] = Field(
        default=None,
        max_length=200,
        description="City / district / area the user is based in.",
        examples=["Mumbai, Maharashtra"],
    )
    fcm_token: Optional[str] = Field(
        default=None,
        description="Firebase Cloud Messaging device token for push notifications.",
    )

    model_config = {"use_enum_values": True}


# ─────────────────────────────────────────────────────────────────────────────
# Create
# ─────────────────────────────────────────────────────────────────────────────


class UserCreate(UserBase):
    """
    Payload used when registering a new user.

    The `password` field is handled directly by Firebase Auth on the client;
    the backend receives only the validated JWT.  We keep it here for
    completeness (e.g. admin-triggered server-side user creation).
    """

    password: Optional[str] = Field(
        default=None,
        min_length=8,
        description="Plain-text password (only used for server-side creation).",
        exclude=True,  # never serialised into responses
    )


# ─────────────────────────────────────────────────────────────────────────────
# Update
# ─────────────────────────────────────────────────────────────────────────────


class UserUpdate(BaseModel):
    """
    All fields are optional – supports partial (PATCH-style) updates.
    """

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, pattern=r"^\+?[0-9\s\-]{7,20}$")
    profile_image_url: Optional[str] = None
    bio: Optional[str] = Field(default=None, max_length=500)
    location: Optional[str] = Field(default=None, max_length=200)
    fcm_token: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# ─────────────────────────────────────────────────────────────────────────────
# Response
# ─────────────────────────────────────────────────────────────────────────────


class UserResponse(UserBase):
    """
    Shape returned to API consumers.
    Includes server-generated metadata (timestamps, active flag).
    """

    is_active: bool = Field(
        default=True,
        description="Whether the account is currently active.",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of account creation.",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the last profile update.",
    )
    last_login: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the user's most recent login.",
    )

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────────────────────


class TokenPayload(BaseModel):
    """
    Decoded Firebase JWT claims as used internally by the auth middleware.
    Not exposed through the public API.
    """

    uid: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: UserRole = UserRole.VOLUNTEER
    email_verified: bool = False


class LoginRequest(BaseModel):
    """Used only in development / testing – prod relies on Firebase client SDK."""

    email: str = Field(..., examples=["admin@svas.org"])
    password: str = Field(..., min_length=8, exclude=True)


class LoginResponse(BaseModel):
    """Returned after a successful server-side login (dev only)."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
