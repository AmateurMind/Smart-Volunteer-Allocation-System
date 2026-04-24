"""
SVAS Backend – Upload Router
Handles multi-format data ingestion: CSV, JSON, plain text, and images.
All uploads are stored in Firestore and optionally processed by Gemini AI.
"""

from __future__ import annotations

import io
import json
import logging
import mimetypes
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from app.config.settings import settings
from app.middleware.auth import get_current_user
from app.services.bigquery_service import BigQueryService, EventType
from app.services.firestore_service import FirestoreService
from app.services.gemini_service import GeminiService
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload-data", tags=["Data Upload"])

# ── Shared service instances (module-level singletons) ────────────────────────
_firestore: Optional[FirestoreService] = None
_gemini: Optional[GeminiService] = None
_bigquery: Optional[BigQueryService] = None


def _get_firestore() -> FirestoreService:
    global _firestore
    if _firestore is None:
        _firestore = FirestoreService()
    return _firestore


def _get_gemini() -> GeminiService:
    global _gemini
    if _gemini is None:
        _gemini = GeminiService()
    return _gemini


def _get_bigquery() -> BigQueryService:
    global _bigquery
    if _bigquery is None:
        _bigquery = BigQueryService()
    return _bigquery


# ── Response models ────────────────────────────────────────────────────────────


class UploadResponse(BaseModel):
    success: bool
    upload_id: str
    records_processed: int
    message: str
    data_type: str
    analysis_result: Optional[Dict[str, Any]] = None
    timestamp: datetime


class UploadRecord(BaseModel):
    id: str
    data_type: str
    status: str
    records_processed: int
    file_name: Optional[str]
    uploaded_by: str
    created_at: datetime
    message: str


# ── Helpers ────────────────────────────────────────────────────────────────────


def _detect_mime(filename: str, content_type: str) -> str:
    """
    Determine the MIME type from the upload's filename and content-type header.
    Falls back to ``application/octet-stream`` if detection fails.
    """
    if content_type and content_type not in (
        "application/octet-stream",
        "binary/octet-stream",
    ):
        return content_type

    guessed, _ = mimetypes.guess_type(filename or "")
    return guessed or content_type or "application/octet-stream"


def _parse_csv(raw_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parse raw CSV bytes into a list of record dicts.

    - Handles UTF-8 and latin-1 encodings.
    - Drops completely empty rows.
    - Converts NaN → None for JSON compatibility.
    - Limits to 10,000 rows to prevent memory issues.

    Raises
    ------
    ValueError
        If the bytes cannot be parsed as a valid CSV.
    """
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(
                io.BytesIO(raw_bytes),
                encoding=encoding,
                on_bad_lines="skip",
                nrows=10_000,
            )
            df = df.dropna(how="all")
            df = df.where(pd.notnull(df), None)
            return df.to_dict(orient="records")
        except (UnicodeDecodeError, pd.errors.EmptyDataError):
            continue
        except Exception as exc:
            raise ValueError(f"CSV parse error: {exc}") from exc

    raise ValueError("Could not decode CSV with UTF-8 or latin-1 encoding.")


def _parse_json(raw_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parse raw JSON bytes into a list of record dicts.

    Accepts either a JSON array ``[…]`` or a single object ``{…}``
    (single objects are wrapped in a list automatically).

    Raises
    ------
    ValueError
        If the bytes are not valid JSON.
    """
    try:
        parsed = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"JSON parse error: {exc}") from exc

    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [parsed]

    raise ValueError("JSON must be an array or an object at the top level.")


def _records_to_text(records: List[Dict[str, Any]]) -> str:
    """
    Flatten a list of record dicts into a human-readable text block that
    Gemini can analyse as a single community need report.
    """
    lines: List[str] = []
    for i, record in enumerate(records[:20], start=1):  # cap at 20 for the prompt
        record_lines = [f"Record {i}:"]
        for key, value in record.items():
            if value is not None and str(value).strip():
                record_lines.append(f"  {key}: {value}")
        lines.append("\n".join(record_lines))
    return "\n\n".join(lines)


def _safe_json(data: Any) -> Any:
    """
    Recursively convert *data* into a JSON-serialisable structure.
    Converts datetime objects to ISO strings, unknown types to strings.
    """
    if isinstance(data, dict):
        return {k: _safe_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_safe_json(v) for v in data]
    if isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, float):
        import math

        if math.isnan(data) or math.isinf(data):
            return None
    return data


# ─────────────────────────────────────────────────────────────────────────────
# POST /upload-data
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload community data (CSV / JSON / text / image)",
    description=(
        "Accepts multi-format community survey data for ingestion into the SVAS "
        "platform.  Optionally triggers AI analysis via Gemini.\n\n"
        "**Supported formats:**\n"
        "- `csv` – spreadsheet / CSV file\n"
        "- `json` – JSON file (array or object)\n"
        "- `text` – plain text field report\n"
        "- `image` – photograph of a paper survey or field situation\n\n"
        "All uploaded records are stored in Firestore and a summary row is "
        "written to BigQuery for analytics."
    ),
)
async def upload_data(
    file: Optional[UploadFile] = File(
        default=None,
        description="CSV, JSON, or image file to upload.",
    ),
    text_data: Optional[str] = Form(
        default=None,
        description="Raw text from a field report (used when data_type='text').",
    ),
    data_type: str = Form(
        default="auto",
        description="One of: csv | json | text | image | auto",
    ),
    auto_analyze: bool = Form(
        default=True,
        description="If True, automatically run AI analysis after ingestion.",
    ),
    current_user: dict = Depends(get_current_user),
) -> UploadResponse:
    """
    Main data ingestion endpoint.

    Flow
    ----
    1. Receive file / text from the request.
    2. Detect / validate the data type.
    3. Parse records (CSV / JSON) or store raw content (text / image).
    4. Persist an upload record to Firestore.
    5. Optionally run Gemini AI analysis on the content.
    6. Log the event to BigQuery.
    7. Return the upload summary.
    """
    fs = _get_firestore()
    gemini = _get_gemini()
    bq = _get_bigquery()
    uid = current_user.get("uid", "anonymous")

    # ── 1. Validate that at least one input was provided ──────────────
    if file is None and not text_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either a file upload or text_data in the form body.",
        )

    # ── 2. Resolve the data type ──────────────────────────────────────
    file_name: Optional[str] = None
    content_type: Optional[str] = None

    if file:
        file_name = file.filename or "upload"
        content_type = _detect_mime(file_name, file.content_type or "")

        if data_type == "auto":
            ext = (file_name.rsplit(".", 1)[-1] if "." in file_name else "").lower()
            if ext == "csv" or "csv" in content_type:
                data_type = "csv"
            elif ext == "json" or "json" in content_type:
                data_type = "json"
            elif content_type.startswith("image/"):
                data_type = "image"
            else:
                data_type = "text"
    elif text_data:
        if data_type == "auto":
            data_type = "text"

    valid_types = {"csv", "json", "text", "image"}
    if data_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data_type '{data_type}'. Must be one of: {valid_types}.",
        )

    # ── 3. Read / parse the content ───────────────────────────────────
    raw_bytes: Optional[bytes] = None
    records: List[Dict[str, Any]] = []
    raw_text: str = ""
    analysis_result: Optional[Dict[str, Any]] = None

    try:
        if data_type == "csv":
            raw_bytes = await file.read()
            records = _parse_csv(raw_bytes)
            raw_text = _records_to_text(records)

        elif data_type == "json":
            raw_bytes = await file.read()
            records = _parse_json(raw_bytes)
            raw_text = _records_to_text(records)

        elif data_type == "text":
            raw_text = text_data or (await file.read()).decode(
                "utf-8", errors="replace"
            )
            records = [{"text": raw_text}]

        elif data_type == "image":
            raw_bytes = await file.read()
            if not raw_bytes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image file is empty.",
                )
            records = []  # populated after AI analysis

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error reading upload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read uploaded content: {exc}",
        ) from exc

    # ── 4. Persist upload record to Firestore ─────────────────────────
    upload_doc: Dict[str, Any] = {
        "uploaded_by": uid,
        "data_type": data_type,
        "file_name": file_name,
        "content_type": content_type,
        "record_count": len(records),
        "status": "PROCESSING",
        "message": f"Received {len(records)} record(s). Processing...",
        "auto_analyze": auto_analyze,
        # Store a trimmed snapshot of the raw data (cap at 50 records)
        "raw_data_preview": _safe_json(records[:50]) if records else [],
        "raw_text_preview": raw_text[:2000] if raw_text else "",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    try:
        upload_id = await fs.create_document(settings.COLLECTION_UPLOADS, upload_doc)
    except Exception as exc:
        logger.error("Failed to persist upload record to Firestore: %s", exc)
        # Generate a fallback ID so the flow can continue
        import uuid

        upload_id = str(uuid.uuid4())

    # ── 5. AI Analysis ────────────────────────────────────────────────
    if auto_analyze:
        try:
            if data_type == "image" and raw_bytes:
                analysis_result = await gemini.analyze_image(
                    raw_bytes, content_type or "image/jpeg"
                )
                # Build a synthetic record from OCR output
                records = [
                    {
                        "source": "image_ocr",
                        "text": analysis_result.get("ocr_text", ""),
                        "category": analysis_result.get("category"),
                        "urgency": analysis_result.get("urgency"),
                        "summary": analysis_result.get("summary"),
                    }
                ]
            elif raw_text:
                analysis_result = await gemini.analyze_text(raw_text)

            if analysis_result:
                logger.info(
                    "AI analysis complete for upload %s: category=%s urgency=%s",
                    upload_id,
                    analysis_result.get("category"),
                    analysis_result.get("urgency"),
                )

        except Exception as exc:
            logger.warning("AI analysis failed for upload %s: %s", upload_id, exc)
            analysis_result = None

    # ── 6. Update Firestore upload record with final status ───────────
    final_status = "ANALYZED" if analysis_result else "INGESTED"
    final_message = f"Successfully processed {len(records)} record(s)" + (
        " and analysed with AI." if analysis_result else "."
    )

    update_payload: Dict[str, Any] = {
        "status": final_status,
        "message": final_message,
        "record_count": len(records),
        "analysis_result": _safe_json(analysis_result) if analysis_result else None,
        "updated_at": datetime.utcnow(),
    }

    try:
        await fs.update_document(settings.COLLECTION_UPLOADS, upload_id, update_payload)
    except Exception as exc:
        logger.warning("Could not update upload record %s: %s", upload_id, exc)

    # ── 7. Log to BigQuery ────────────────────────────────────────────
    try:
        await bq.log_event(
            EventType.DATA_UPLOADED,
            {
                "user_uid": uid,
                "need_id": upload_id,
                "category": analysis_result.get("category")
                if analysis_result
                else None,
                "urgency": analysis_result.get("urgency") if analysis_result else None,
                "location": analysis_result.get("location_hints")
                if analysis_result
                else None,
                "data_type": data_type,
                "record_count": len(records),
            },
        )
    except Exception as exc:
        logger.debug("BigQuery log_event failed (non-critical): %s", exc)

    return UploadResponse(
        success=True,
        upload_id=upload_id,
        records_processed=len(records),
        message=final_message,
        data_type=data_type,
        analysis_result=analysis_result,
        timestamp=datetime.utcnow(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /upload-data/history
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/history",
    summary="Get recent upload history",
    description="Returns the most recent data uploads for the current user or all users (admin).",
)
async def get_upload_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return recent upload records from Firestore."""
    fs = _get_firestore()
    limit = min(limit, 100)

    try:
        uploads = await fs.get_recent_uploads(limit=limit)
        # Sanitise datetime objects for JSON serialisation
        uploads = _safe_json(uploads)
    except Exception as exc:
        logger.error("Failed to fetch upload history: %s", exc)
        uploads = []

    return {
        "uploads": uploads,
        "count": len(uploads),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /upload-data/{upload_id}
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/{upload_id}",
    summary="Get a specific upload record",
    description="Retrieve a single upload record by its Firestore document ID.",
)
async def get_upload(
    upload_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fetch a single upload record from Firestore."""
    fs = _get_firestore()

    upload = await fs.get_document(settings.COLLECTION_UPLOADS, upload_id)
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload record '{upload_id}' not found.",
        )

    return _safe_json(upload)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /upload-data/{upload_id}
# ─────────────────────────────────────────────────────────────────────────────


@router.delete(
    "/{upload_id}",
    summary="Delete an upload record",
    status_code=status.HTTP_200_OK,
)
async def delete_upload(
    upload_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Delete an upload record from Firestore.
    Note: this does NOT delete any Need documents created from this upload.
    """
    fs = _get_firestore()
    uid = current_user.get("uid")

    # Verify the record exists
    upload = await fs.get_document(settings.COLLECTION_UPLOADS, upload_id)
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload record '{upload_id}' not found.",
        )

    # Only the uploader or an admin may delete
    if (
        upload.get("uploaded_by") != uid
        and current_user.get("resolved_role") != "ADMIN"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this upload record.",
        )

    deleted = await fs.delete_document(settings.COLLECTION_UPLOADS, upload_id)
    return {
        "success": deleted,
        "message": f"Upload record '{upload_id}' deleted."
        if deleted
        else "Record not found or already deleted.",
    }
