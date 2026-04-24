"""
SVAS Backend – Gemini AI Service
Wraps the Google Generative AI SDK to provide text analysis, image OCR,
batch processing, and volunteer-match explanations via Gemini 1.5 Flash.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from app.config.settings import settings
from google.generativeai.types import HarmBlockThreshold, HarmCategory

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Prompt templates
# ─────────────────────────────────────────────────────────────────────────────

_ANALYSIS_SYSTEM_PROMPT = """
You are an AI assistant for SVAS (Smart Volunteer Allocation System), an NGO
volunteer management platform operating in India.

Your job is to analyse community need reports submitted by field workers and
return a structured JSON object.  The report may be raw survey text, a
transcription of a paper form, or notes from a field visit.

Return ONLY a valid JSON object — no markdown fences, no prose, no comments.

JSON schema to follow exactly:
{
  "category":                "FOOD" | "HEALTH" | "EDUCATION" | "SHELTER" | "CLOTHING" | "OTHER",
  "urgency":                 "HIGH" | "MEDIUM" | "LOW",
  "summary":                 "<1–2 sentence plain-English summary of the core need>",
  "key_needs":               ["<specific item or action>", ...],
  "estimated_beneficiaries": <integer> | null,
  "recommended_skills":      ["MEDICAL" | "EDUCATION" | "LOGISTICS" | "COUNSELING" | "DRIVING" | "COOKING" | "GENERAL", ...],
  "location_hints":          "<any location information extracted from the text>" | null,
  "confidence":              <float 0.0–1.0 reflecting how certain you are of the classification>
}

Classification guidelines:
- FOOD      → hunger, food shortage, ration kits, malnutrition, drinking water
- HEALTH    → medical aid, medicine, doctor, hospital, injury, disease outbreak, sanitation
- EDUCATION → school supplies, tuition, literacy, scholarships, dropout risk
- SHELTER   → homeless, flood/fire displacement, temporary housing, tarpaulins
- CLOTHING  → winter clothing, blankets, school uniforms
- OTHER     → anything that doesn't fit the above

Urgency guidelines:
- HIGH   → life-threatening, immediate danger, disaster aftermath (respond within 24 h)
- MEDIUM → serious but not immediately life-threatening (respond within 72 h)
- LOW    → important but can be planned (respond within 2 weeks)

recommended_skills must be a subset of:
  MEDICAL, EDUCATION, LOGISTICS, COUNSELING, DRIVING, COOKING, GENERAL

If a field cannot be determined from the text, use null (for scalars) or [] (for arrays).
""".strip()

_IMAGE_SYSTEM_PROMPT = """
You are an AI assistant for SVAS (Smart Volunteer Allocation System).

The attached image is a photograph of a community survey form, field report,
handwritten notes, or an on-site situation that documents a community need.

1. First, perform OCR on any visible text.
2. Combine the extracted text with the visual context to understand the need.
3. Return ONLY a valid JSON object matching this schema exactly:

{
  "ocr_text":                "<all readable text extracted from the image>",
  "category":                "FOOD" | "HEALTH" | "EDUCATION" | "SHELTER" | "CLOTHING" | "OTHER",
  "urgency":                 "HIGH" | "MEDIUM" | "LOW",
  "summary":                 "<1–2 sentence summary>",
  "key_needs":               ["<item or action>", ...],
  "estimated_beneficiaries": <integer> | null,
  "recommended_skills":      ["MEDICAL" | "EDUCATION" | "LOGISTICS" | "COUNSELING" | "DRIVING" | "COOKING" | "GENERAL", ...],
  "location_hints":          "<location info if visible>" | null,
  "confidence":              <float 0.0–1.0>
}

No markdown, no explanation — raw JSON only.
""".strip()

_MATCH_EXPLANATION_PROMPT = """
You are a coordinator at an NGO volunteer management system.

Write a concise, warm, professional 2–3 sentence explanation of why the
following volunteer is a good match for the described community need.
Focus on skill alignment, proximity, and availability.
Do NOT mention specific score numbers.  Write in plain English.
""".strip()

# ─────────────────────────────────────────────────────────────────────────────
# Fallback / mock result (used when Gemini is unavailable in dev mode)
# ─────────────────────────────────────────────────────────────────────────────

_MOCK_ANALYSIS: Dict[str, Any] = {
    "category": "OTHER",
    "urgency": "LOW",
    "summary": "Mock analysis result – Gemini API key not configured.",
    "key_needs": ["configure GEMINI_API_KEY in .env"],
    "estimated_beneficiaries": None,
    "recommended_skills": ["GENERAL"],
    "location_hints": None,
    "confidence": 0.0,
    "raw_model_output": None,
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _extract_json(raw: str) -> Dict[str, Any]:
    """
    Robustly extract a JSON object from *raw* model output.

    The model is instructed to return bare JSON, but may occasionally wrap it
    in markdown fences (```json … ```).  This helper strips fences first, then
    parses the JSON.  Raises ``ValueError`` if no valid JSON object is found.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

    # Attempt direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find the first {...} block via regex as a last resort
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from model output:\n{raw[:500]}")


def _safety_settings() -> Dict[HarmCategory, HarmBlockThreshold]:
    """
    Return permissive safety settings so that descriptions of disasters,
    illness, or poverty are not incorrectly blocked.
    """
    return {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GeminiService
# ─────────────────────────────────────────────────────────────────────────────


class GeminiService:
    """
    Async-compatible service that wraps the Gemini 1.5 Flash model.

    All public methods are ``async`` and safe to call from FastAPI route
    handlers without blocking the event loop (the underlying SDK calls are
    synchronous but fast enough not to need a thread executor at this stage;
    swap for ``asyncio.to_thread`` if latency becomes an issue).

    Usage
    -----
    ::

        gemini = GeminiService()
        result = await gemini.analyze_text("200 flood-displaced families in Ward 7 ...")
    """

    def __init__(self) -> None:
        self._ready = False
        self._model: Optional[genai.GenerativeModel] = None
        self._vision_model: Optional[genai.GenerativeModel] = None
        self._init()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init(self) -> None:
        """Configure the Gemini SDK.  Logs a warning if the key is missing."""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning(
                "GEMINI_API_KEY is not set.  GeminiService will return mock "
                "responses.  Set GEMINI_API_KEY in your .env file to enable AI."
            )
            return

        try:
            genai.configure(api_key=api_key)

            generation_config = genai.GenerationConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                response_mime_type="text/plain",  # we parse JSON ourselves
            )

            self._model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config=generation_config,
                safety_settings=_safety_settings(),
                system_instruction=_ANALYSIS_SYSTEM_PROMPT,
            )

            # Vision model shares the same settings but uses a different
            # system instruction (injected per-request via chat history).
            self._vision_model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config=generation_config,
                safety_settings=_safety_settings(),
            )

            self._ready = True
            logger.info(
                "GeminiService initialised with model '%s'.", settings.GEMINI_MODEL
            )

        except Exception as exc:  # noqa: BLE001
            logger.error("GeminiService initialisation failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyse a plain-text community need report.

        Parameters
        ----------
        text : str
            Raw survey / field report text in any language.

        Returns
        -------
        dict
            Parsed ``NeedAnalysisResult``-compatible dict with keys:
            ``category``, ``urgency``, ``summary``, ``key_needs``,
            ``estimated_beneficiaries``, ``recommended_skills``,
            ``location_hints``, ``confidence``, ``raw_model_output``.
        """
        if not self._ready or self._model is None:
            logger.debug("GeminiService not ready – returning mock analysis.")
            return dict(_MOCK_ANALYSIS)

        if not text or not text.strip():
            return {
                **_MOCK_ANALYSIS,
                "summary": "Empty text provided – nothing to analyse.",
            }

        try:
            prompt = (
                "Analyse the following community need report and return the "
                "structured JSON as instructed:\n\n"
                f"{text.strip()}"
            )
            response = self._model.generate_content(prompt)
            raw_output = response.text or ""
            result = _extract_json(raw_output)
            result["raw_model_output"] = raw_output
            # Ensure all expected keys are present
            result = _fill_defaults(result)
            logger.debug("Text analysis completed. category=%s", result.get("category"))
            return result

        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini text analysis failed: %s", exc)
            return {
                **_MOCK_ANALYSIS,
                "summary": f"Analysis failed: {exc}",
                "raw_model_output": str(exc),
            }

    async def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Perform OCR and need analysis on an image of a survey or field report.

        Parameters
        ----------
        image_bytes : bytes
            Raw image file bytes (JPEG, PNG, WebP, or PDF first page).
        mime_type : str
            MIME type of the image (default ``"image/jpeg"``).

        Returns
        -------
        dict
            Same structure as :meth:`analyze_text` plus an ``ocr_text`` key
            containing the raw extracted text.
        """
        if not self._ready or self._vision_model is None:
            logger.debug("GeminiService not ready – returning mock image analysis.")
            return {**_MOCK_ANALYSIS, "ocr_text": ""}

        if not image_bytes:
            return {
                **_MOCK_ANALYSIS,
                "ocr_text": "",
                "summary": "Empty image provided.",
            }

        try:
            image_part = {
                "mime_type": mime_type,
                "data": image_bytes,
            }
            prompt_parts = [
                _IMAGE_SYSTEM_PROMPT,
                "\n\nImage to analyse:\n",
                image_part,
            ]
            response = self._vision_model.generate_content(prompt_parts)
            raw_output = response.text or ""
            result = _extract_json(raw_output)
            result["raw_model_output"] = raw_output
            result = _fill_defaults(result)
            result.setdefault("ocr_text", "")
            logger.debug(
                "Image analysis completed. category=%s ocr_chars=%d",
                result.get("category"),
                len(result.get("ocr_text", "")),
            )
            return result

        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini image analysis failed: %s", exc)
            return {
                **_MOCK_ANALYSIS,
                "ocr_text": "",
                "summary": f"Image analysis failed: {exc}",
                "raw_model_output": str(exc),
            }

    async def batch_analyze(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyse multiple need-report texts sequentially.

        Parameters
        ----------
        texts : list[str]
            List of raw text strings to analyse.

        Returns
        -------
        list[dict]
            One analysis result dict per input text, in the same order.
            Individual failures return a mock result rather than raising.
        """
        results: List[Dict[str, Any]] = []
        for idx, text in enumerate(texts):
            logger.debug("Batch analyse: processing item %d / %d", idx + 1, len(texts))
            result = await self.analyze_text(text)
            results.append(result)
        return results

    async def generate_match_explanation(
        self,
        volunteer: Dict[str, Any],
        need: Dict[str, Any],
    ) -> str:
        """
        Generate a human-readable explanation of why a volunteer is a good
        match for a particular community need.

        Parameters
        ----------
        volunteer : dict
            Volunteer profile dict (must include ``name``, ``skills``,
            ``location``).
        need : dict
            Need record dict (must include ``title``, ``category``,
            ``location``, ``recommended_skills``).

        Returns
        -------
        str
            A 2–3 sentence natural-language explanation.
        """
        if not self._ready or self._model is None:
            return (
                f"{volunteer.get('name', 'This volunteer')} is a suitable match "
                f"for the '{need.get('title', 'need')}' based on their skills and location."
            )

        vol_name = volunteer.get("name", "The volunteer")
        vol_skills = ", ".join(volunteer.get("skills", []) or ["GENERAL"])
        vol_location = volunteer.get("location", "unknown location")
        vol_tasks_done = volunteer.get("tasks_completed", 0)

        need_title = need.get("title", "community need")
        need_category = need.get("category", "OTHER")
        need_location = need.get("location", "unknown location")
        need_skills = ", ".join(need.get("recommended_skills", []) or ["GENERAL"])

        prompt = (
            f"{_MATCH_EXPLANATION_PROMPT}\n\n"
            f"Volunteer:\n"
            f"  Name: {vol_name}\n"
            f"  Skills: {vol_skills}\n"
            f"  Location: {vol_location}\n"
            f"  Tasks completed: {vol_tasks_done}\n\n"
            f"Need:\n"
            f"  Title: {need_title}\n"
            f"  Category: {need_category}\n"
            f"  Location: {need_location}\n"
            f"  Required skills: {need_skills}\n\n"
            f"Write the 2–3 sentence match explanation:"
        )

        try:
            # Use a bare model without the JSON system instruction for prose output
            prose_model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=256,
                ),
                safety_settings=_safety_settings(),
            )
            response = prose_model.generate_content(prompt)
            explanation = (response.text or "").strip()
            return explanation if explanation else _default_explanation(volunteer, need)

        except Exception as exc:  # noqa: BLE001
            logger.warning("Match explanation generation failed: %s", exc)
            return _default_explanation(volunteer, need)

    async def extract_location_coordinates(
        self, location_text: str
    ) -> Optional[Dict[str, float]]:
        """
        Ask Gemini to infer approximate GPS coordinates for a textual location
        description (best-effort; not a geocoding API replacement).

        Parameters
        ----------
        location_text : str
            Human-readable location such as "Ward 7, Dharavi, Mumbai, Maharashtra".

        Returns
        -------
        dict or None
            ``{"latitude": float, "longitude": float}`` or ``None`` if
            Gemini cannot determine the coordinates with reasonable confidence.
        """
        if not self._ready or self._model is None:
            return None

        prompt = (
            "Return the approximate GPS coordinates for the following location in India "
            "as a JSON object with keys 'latitude' and 'longitude'. "
            "If you are not reasonably confident, return null.\n\n"
            f"Location: {location_text}\n\n"
            "JSON response only:"
        )

        try:
            bare_model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config=genai.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=64,
                ),
                safety_settings=_safety_settings(),
            )
            response = bare_model.generate_content(prompt)
            raw = response.text or ""
            data = _extract_json(raw)
            lat = data.get("latitude")
            lng = data.get("longitude")
            if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                return {"latitude": float(lat), "longitude": float(lng)}
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Coordinate extraction failed for '%s': %s", location_text, exc
            )

        return None

    @property
    def is_ready(self) -> bool:
        """Return ``True`` if the Gemini SDK is initialised and ready."""
        return self._ready


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────


def _fill_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure all expected keys are present in *data*, back-filling with safe
    defaults so callers never receive a ``KeyError``.
    """
    defaults: Dict[str, Any] = {
        "category": "OTHER",
        "urgency": "LOW",
        "summary": "",
        "key_needs": [],
        "estimated_beneficiaries": None,
        "recommended_skills": [],
        "location_hints": None,
        "confidence": None,
        "raw_model_output": None,
    }
    for key, default_val in defaults.items():
        data.setdefault(key, default_val)

    # Normalise enum strings to uppercase
    for enum_field in ("category", "urgency"):
        if isinstance(data.get(enum_field), str):
            data[enum_field] = data[enum_field].upper()

    if isinstance(data.get("recommended_skills"), list):
        data["recommended_skills"] = [
            s.upper() for s in data["recommended_skills"] if isinstance(s, str)
        ]

    return data


def _default_explanation(
    volunteer: Dict[str, Any],
    need: Dict[str, Any],
) -> str:
    """Return a simple template-based match explanation as a fallback."""
    name = volunteer.get("name", "This volunteer")
    skills = volunteer.get("skills", [])
    need_title = need.get("title", "this need")
    location = volunteer.get("location", "the area")

    skill_str = (
        f"Their skills in {', '.join(skills[:2])}"
        if skills
        else "Their general volunteering experience"
    )

    return (
        f"{name} is a strong candidate for '{need_title}'. "
        f"{skill_str} align well with the requirements of this need. "
        f"They are based in {location}, making them well-positioned to assist promptly."
    )
