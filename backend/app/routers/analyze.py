"""
SVAS Backend – /analyze Router
Gemini-powered community need analysis endpoints.
Accepts raw text or batch texts, calls GeminiService, persists results to
Firestore, logs events to BigQuery, and returns structured NeedAnalysisResult.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.middleware.auth import get_current_user
from app.models.need import NeedAnalysisResult, NeedCategory, NeedCreate, UrgencyLevel
from app.services.bigquery_service import BigQueryService, EventType
from app.services.firestore_service import FirestoreService
from app.services.gemini_service import GeminiService
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analyze",
    tags=["Analysis"],
)

# ── Shared service singletons (created once, reused across requests) ──────────
_gemini: Optional[GeminiService] = None
_firestore: Optional[FirestoreService] = None
_bigquery: Optional[BigQueryService] = None


def _get_gemini() -> GeminiService:
    global _gemini
    if _gemini is None:
        _gemini = GeminiService()
    return _gemini


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


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response schemas (local to this router)
# ─────────────────────────────────────────────────────────────────────────────


class AnalyzeTextRequest(BaseModel):
    """Request body for the single-text analysis endpoint."""

    text: str = Field(
        ...,
        min_length=10,
        max_length=10_000,
        description="Raw community-need report text to analyse.",
        examples=[
            "200 families displaced by flooding in Ward 7, Dharavi. "
            "They urgently need food packets, clean water, and temporary shelter. "
            "Many children have not eaten in 24 hours."
        ],
    )
    upload_id: Optional[str] = Field(
        default=None,
        description=(
            "If this analysis is linked to an upload record, "
            "provide its Firestore document ID to update the upload status."
        ),
    )
    save_as_need: bool = Field(
        default=True,
        description=(
            "If True, a Need document is automatically created in Firestore "
            "from the analysis result."
        ),
    )
    location: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Optional pre-known location to attach to the created Need.",
    )
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)


class AnalyzeTextResponse(BaseModel):
    """Response returned by the single-text analysis endpoint."""

    analysis: NeedAnalysisResult
    need_id: Optional[str] = Field(
        default=None,
        description="Firestore document ID of the newly created Need, if saved.",
    )
    upload_id: Optional[str] = Field(
        default=None,
        description="Echo of the upload_id if one was supplied.",
    )
    message: str = Field(default="Analysis completed successfully.")


class BatchAnalyzeRequest(BaseModel):
    """Request body for the batch analysis endpoint."""

    texts: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of raw text strings to analyse (max 50 per request).",
        examples=[
            [
                "Food shortage in Andheri East – 300 families affected.",
                "Medical camp needed in Govandi – dengue outbreak reported.",
            ]
        ],
    )
    save_as_needs: bool = Field(
        default=True,
        description="If True, a Need document is created for each analysis result.",
    )
    upload_id: Optional[str] = Field(
        default=None,
        description="Upload record ID to link all generated needs to.",
    )


class BatchAnalyzeResponse(BaseModel):
    """Response returned by the batch analysis endpoint."""

    total: int = Field(..., description="Number of texts submitted.")
    processed: int = Field(..., description="Number successfully analysed.")
    failed: int = Field(..., description="Number that failed analysis.")
    results: List[Dict[str, Any]] = Field(
        ..., description="One result object per input text, in the same order."
    )
    need_ids: List[Optional[str]] = Field(
        default_factory=list,
        description="Firestore document IDs of created needs (None where creation failed).",
    )
    message: str = Field(default="Batch analysis completed.")


class AnalyzeFromUploadRequest(BaseModel):
    """Re-analyse an existing upload record."""

    upload_id: str = Field(
        ...,
        description="Firestore document ID of the upload to re-analyse.",
    )
    save_as_needs: bool = Field(
        default=True,
        description="Create Need documents from each analysed record.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _analysis_to_need_data(
    analysis: Dict[str, Any],
    reported_by: str,
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    upload_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert a raw Gemini analysis dict into a Firestore-ready Need document.

    Parameters
    ----------
    analysis : dict
        Output from ``GeminiService.analyze_text`` / ``analyze_image``.
    reported_by : str
        UID of the authenticated user who triggered the analysis.
    location : str, optional
        Human-readable location string to use; falls back to ``location_hints``
        extracted by the AI if not provided.
    latitude, longitude : float, optional
        GPS coordinates for the need location.
    upload_id : str, optional
        Reference to the source upload record.

    Returns
    -------
    dict
        Ready-to-insert Firestore document payload.
    """
    now = datetime.utcnow()

    # Resolve location: caller-supplied > AI hints > default
    resolved_location = (
        location or analysis.get("location_hints") or "Location not specified"
    )

    return {
        "title": _generate_title(analysis),
        "description": analysis.get("summary", "No description available."),
        "category": analysis.get("category", "OTHER"),
        "urgency": analysis.get("urgency", "LOW"),
        "location": resolved_location,
        "latitude": latitude,
        "longitude": longitude,
        "reported_by": reported_by,
        "beneficiary_count": analysis.get("estimated_beneficiaries"),
        "key_needs": analysis.get("key_needs", []),
        "recommended_skills": analysis.get("recommended_skills", []),
        "ai_summary": analysis.get("summary"),
        "upload_id": upload_id,
        "tags": _generate_tags(analysis),
        "status": "OPEN",
        "assigned_volunteer_ids": [],
        "task_ids": [],
        "created_at": now,
        "updated_at": now,
    }


def _generate_title(analysis: Dict[str, Any]) -> str:
    """
    Create a short, descriptive title from the analysis result.
    Tries to extract the first sentence of the summary; falls back to a
    category/urgency description.
    """
    summary = analysis.get("summary", "")
    if summary:
        # Use the first sentence (up to 80 chars)
        first_sentence = summary.split(".")[0].strip()
        if first_sentence and len(first_sentence) <= 80:
            return first_sentence
        if first_sentence:
            return first_sentence[:77] + "..."

    category = analysis.get("category", "OTHER").title()
    urgency = analysis.get("urgency", "MEDIUM").title()
    location = analysis.get("location_hints") or "Unknown area"
    return f"{urgency} priority {category} need – {location}"


def _generate_tags(analysis: Dict[str, Any]) -> List[str]:
    """Derive relevant tags from the analysis result."""
    tags: List[str] = []
    category = analysis.get("category")
    urgency = analysis.get("urgency")

    if category:
        tags.append(category.lower())
    if urgency:
        tags.append(urgency.lower())

    # Add key-need keywords as tags (normalised, deduped)
    for kn in analysis.get("key_needs", [])[:5]:
        tag = kn.lower().replace(" ", "-")[:30]
        if tag and tag not in tags:
            tags.append(tag)

    return tags[:10]  # cap at 10 tags


async def _log_analysis_event(
    bq: BigQueryService,
    analysis: Dict[str, Any],
    user_uid: str,
    need_id: Optional[str],
) -> None:
    """Fire-and-forget BigQuery event log for an analysis action."""
    try:
        await bq.log_event(
            EventType.DATA_ANALYZED,
            {
                "user_uid": user_uid,
                "need_id": need_id,
                "category": analysis.get("category"),
                "urgency": analysis.get("urgency"),
                "estimated_beneficiaries": analysis.get("estimated_beneficiaries"),
                "confidence": analysis.get("confidence"),
            },
        )
        if need_id:
            await bq.log_event(
                EventType.NEED_CREATED,
                {
                    "user_uid": user_uid,
                    "need_id": need_id,
                    "category": analysis.get("category"),
                    "urgency": analysis.get("urgency"),
                    "location": analysis.get("location_hints"),
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Background BigQuery log failed: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=AnalyzeTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyse a community need report",
    description=(
        "Send raw text from a survey, field report, or manual entry to Gemini "
        "for AI-powered categorisation and urgency classification. "
        "Optionally creates a Need record in Firestore."
    ),
)
async def analyze_text(
    request: AnalyzeTextRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> AnalyzeTextResponse:
    """
    Analyse a single community need report text.

    - Calls **Gemini 1.5 Flash** to classify category, urgency, key needs, etc.
    - Optionally persists the result as a **Need** document in Firestore.
    - Optionally updates the linked **upload record** status.
    - Logs ``DATA_ANALYZED`` and (if saved) ``NEED_CREATED`` events to BigQuery.
    """
    gemini = _get_gemini()
    firestore = _get_firestore()
    bigquery = _get_bigquery()
    user_uid: str = current_user.get("uid", "anonymous")

    # ── 1. Run AI analysis ────────────────────────────────────────────
    logger.info("analyze_text: starting analysis for user '%s'", user_uid)
    raw_analysis = await gemini.analyze_text(request.text)

    # Validate / coerce enums so Pydantic doesn't reject unexpected values
    raw_analysis["category"] = _coerce_category(raw_analysis.get("category"))
    raw_analysis["urgency"] = _coerce_urgency(raw_analysis.get("urgency"))

    try:
        analysis_result = NeedAnalysisResult(**raw_analysis)
    except Exception as exc:
        logger.error("NeedAnalysisResult validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI returned an unexpected response format: {exc}",
        )

    # ── 2. Persist as Need (optional) ─────────────────────────────────
    need_id: Optional[str] = None
    if request.save_as_need:
        need_data = _analysis_to_need_data(
            raw_analysis,
            reported_by=user_uid,
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude,
            upload_id=request.upload_id,
        )
        try:
            need_id = await firestore.create_document(
                settings.COLLECTION_NEEDS, need_data
            )
            logger.info("analyze_text: created Need '%s' from analysis.", need_id)
        except Exception as exc:
            logger.error("Failed to create Need document: %s", exc)
            # Non-fatal – return analysis even if Firestore write fails

    # ── 3. Update linked upload record ────────────────────────────────
    if request.upload_id:
        try:
            await firestore.update_upload_status(
                request.upload_id,
                status="ANALYSED",
                extra={
                    "need_id": need_id,
                    "analysis_category": raw_analysis.get("category"),
                },
            )
        except Exception as exc:
            logger.warning("Could not update upload status: %s", exc)

    # ── 4. Log analytics events in background ─────────────────────────
    background_tasks.add_task(
        _log_analysis_event, bigquery, raw_analysis, user_uid, need_id
    )

    return AnalyzeTextResponse(
        analysis=analysis_result,
        need_id=need_id,
        upload_id=request.upload_id,
        message=(
            "Analysis completed and Need record created."
            if need_id
            else "Analysis completed."
        ),
    )


@router.post(
    "/batch",
    response_model=BatchAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch-analyse multiple need reports",
    description=(
        "Submit up to 50 community need report texts in a single call. "
        "Each text is analysed individually by Gemini and optionally saved as "
        "a Need document in Firestore."
    ),
)
async def batch_analyze(
    request: BatchAnalyzeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> BatchAnalyzeResponse:
    """
    Analyse multiple need-report texts in one request.

    Results are returned in the same order as the input list.
    Individual failures do not abort the batch; they return a partial/mock
    result with ``"category": "OTHER"`` and ``"confidence": 0``.
    """
    if len(request.texts) > 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Maximum 50 texts per batch request.",
        )

    gemini = _get_gemini()
    firestore = _get_firestore()
    bigquery = _get_bigquery()
    user_uid: str = current_user.get("uid", "anonymous")

    logger.info(
        "batch_analyze: processing %d texts for user '%s'", len(request.texts), user_uid
    )

    # ── 1. Batch analysis ─────────────────────────────────────────────
    raw_results = await gemini.batch_analyze(request.texts)

    results_out: List[Dict[str, Any]] = []
    need_ids: List[Optional[str]] = []
    processed = 0
    failed = 0
    bq_events: List[Dict[str, Any]] = []

    for idx, (text, raw) in enumerate(zip(request.texts, raw_results)):
        raw["category"] = _coerce_category(raw.get("category"))
        raw["urgency"] = _coerce_urgency(raw.get("urgency"))

        is_mock = raw.get("confidence", 1.0) == 0.0 and not raw.get("summary")

        need_id: Optional[str] = None

        # ── 2. Persist each result as a Need ──────────────────────────
        if request.save_as_needs and not is_mock:
            need_data = _analysis_to_need_data(
                raw,
                reported_by=user_uid,
                upload_id=request.upload_id,
            )
            try:
                need_id = await firestore.create_document(
                    settings.COLLECTION_NEEDS, need_data
                )
            except Exception as exc:
                logger.warning("Batch: failed to create Need for item %d: %s", idx, exc)

        if is_mock or raw.get("confidence", 1.0) == 0.0:
            failed += 1
        else:
            processed += 1

        results_out.append(
            {
                "index": idx,
                "category": raw.get("category"),
                "urgency": raw.get("urgency"),
                "summary": raw.get("summary"),
                "key_needs": raw.get("key_needs", []),
                "recommended_skills": raw.get("recommended_skills", []),
                "estimated_beneficiaries": raw.get("estimated_beneficiaries"),
                "location_hints": raw.get("location_hints"),
                "confidence": raw.get("confidence"),
                "need_id": need_id,
            }
        )
        need_ids.append(need_id)

        # Collect BQ events
        bq_events.append(
            {
                "event_type": EventType.DATA_ANALYZED,
                "user_uid": user_uid,
                "need_id": need_id,
                "category": raw.get("category"),
                "urgency": raw.get("urgency"),
            }
        )
        if need_id:
            bq_events.append(
                {
                    "event_type": EventType.NEED_CREATED,
                    "user_uid": user_uid,
                    "need_id": need_id,
                    "category": raw.get("category"),
                    "urgency": raw.get("urgency"),
                }
            )

    # ── 3. Update linked upload ────────────────────────────────────────
    if request.upload_id:
        try:
            await firestore.update_upload_status(
                request.upload_id,
                status="ANALYSED",
                extra={"needs_created": processed},
            )
        except Exception as exc:
            logger.warning("Could not update upload status: %s", exc)

    # ── 4. Batch BigQuery log in background ───────────────────────────
    if bq_events:
        background_tasks.add_task(bigquery.log_events_batch, bq_events)

    return BatchAnalyzeResponse(
        total=len(request.texts),
        processed=processed,
        failed=failed,
        results=results_out,
        need_ids=need_ids,
        message=f"Batch complete: {processed} analysed, {failed} failed.",
    )


@router.post(
    "/from-upload",
    response_model=BatchAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-analyse an existing upload",
    description=(
        "Fetch a previously uploaded dataset from Firestore and run AI analysis "
        "on each text record it contains."
    ),
)
async def analyze_from_upload(
    request: AnalyzeFromUploadRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> BatchAnalyzeResponse:
    """
    Re-analyse all text records stored in an upload document.

    The upload document must have a ``raw_data`` field that is either a list
    of strings or a list of dicts each containing a ``text`` / ``description``
    / ``notes`` key.
    """
    firestore = _get_firestore()
    user_uid: str = current_user.get("uid", "anonymous")

    # Fetch upload record
    upload = await firestore.get_document(
        settings.COLLECTION_UPLOADS, request.upload_id
    )
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload record '{request.upload_id}' not found.",
        )

    raw_data = upload.get("raw_data", [])
    if not raw_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Upload record has no raw_data to analyse.",
        )

    # Normalise raw_data → list of strings
    texts: List[str] = []
    for item in raw_data:
        if isinstance(item, str):
            texts.append(item)
        elif isinstance(item, dict):
            # Try common field names
            text_val = (
                item.get("text")
                or item.get("description")
                or item.get("notes")
                or item.get("content")
                or item.get("report")
                or str(item)
            )
            texts.append(str(text_val))

    if not texts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract any text strings from the upload's raw_data.",
        )

    # Cap at 50 to reuse the batch endpoint logic
    texts = texts[:50]

    # Delegate to batch analysis
    batch_request = BatchAnalyzeRequest(
        texts=texts,
        save_as_needs=request.save_as_needs,
        upload_id=request.upload_id,
    )
    return await batch_analyze(batch_request, background_tasks, current_user)


@router.get(
    "/needs",
    status_code=status.HTTP_200_OK,
    summary="List analysed needs",
    description="Return all Need documents from Firestore with optional filters.",
)
async def list_needs(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    urgency: Optional[str] = Query(default=None, description="Filter by urgency"),
    status_filter: Optional[str] = Query(
        default=None, alias="status", description="Filter by status"
    ),
    limit: int = Query(default=20, ge=1, le=100, description="Max results to return"),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Retrieve stored Need records with optional category/urgency/status filters.
    """
    firestore = _get_firestore()

    filters = []
    if category:
        filters.append(("category", "==", category.upper()))
    if urgency:
        filters.append(("urgency", "==", urgency.upper()))
    if status_filter:
        filters.append(("status", "==", status_filter.upper()))

    needs = await firestore.query_collection(
        settings.COLLECTION_NEEDS,
        filters=filters if filters else None,
        order_by="created_at",
        descending=True,
        limit=limit,
    )

    return {
        "total": len(needs),
        "needs": needs,
        "filters_applied": {
            "category": category,
            "urgency": urgency,
            "status": status_filter,
        },
    }


@router.get(
    "/needs/{need_id}",
    status_code=status.HTTP_200_OK,
    summary="Get a single need record",
)
async def get_need(
    need_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fetch a single Need document by its Firestore ID."""
    firestore = _get_firestore()
    need = await firestore.get_document(settings.COLLECTION_NEEDS, need_id)
    if not need:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Need '{need_id}' not found.",
        )
    return need


@router.delete(
    "/needs/{need_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a need record",
)
async def delete_need(
    need_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Soft-delete a Need document by setting its status to CLOSED.
    Requires ADMIN or COORDINATOR role.
    """
    firestore = _get_firestore()

    role = current_user.get("resolved_role", current_user.get("role", "VOLUNTEER"))
    if role not in ("ADMIN", "COORDINATOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN or COORDINATOR can delete need records.",
        )

    updated = await firestore.update_document(
        settings.COLLECTION_NEEDS,
        need_id,
        {"status": "CLOSED", "updated_at": datetime.utcnow()},
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Need '{need_id}' not found.",
        )
    return {"message": f"Need '{need_id}' closed successfully.", "need_id": need_id}


# ─────────────────────────────────────────────────────────────────────────────
# Private enum-coercion helpers
# ─────────────────────────────────────────────────────────────────────────────

_VALID_CATEGORIES = {c.value for c in NeedCategory}
_VALID_URGENCIES = {u.value for u in UrgencyLevel}


def _coerce_category(value: Optional[str]) -> str:
    """Return a valid NeedCategory string; falls back to OTHER."""
    if not value:
        return "OTHER"
    upper = value.upper()
    return upper if upper in _VALID_CATEGORIES else "OTHER"


def _coerce_urgency(value: Optional[str]) -> str:
    """Return a valid UrgencyLevel string; falls back to LOW."""
    if not value:
        return "LOW"
    upper = value.upper()
    return upper if upper in _VALID_URGENCIES else "LOW"
