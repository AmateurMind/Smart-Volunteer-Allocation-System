"""
SVAS Backend – Firestore Service
Async-compatible wrapper around the Firebase Admin Firestore client.
All blocking SDK calls are offloaded to a thread-pool executor so they
don't block the FastAPI event-loop.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from functools import partial
from typing import Any, Dict, List, Optional, Tuple

import firebase_admin
from app.config.settings import settings
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level Firebase initialisation (idempotent)
# ---------------------------------------------------------------------------


def _init_firebase() -> None:
    """
    Initialise the Firebase Admin SDK exactly once.

    Priority order for credentials:
      1. Service-account JSON key file (path from settings)
      2. Application Default Credentials (Cloud Run / GCE metadata server)
    """
    if firebase_admin._apps:
        return  # already initialised

    try:
        if settings.service_account_key_exists:
            cred = credentials.Certificate(settings.service_account_key_path)
            logger.info(
                "Firebase initialised with service-account key: %s",
                settings.service_account_key_path,
            )
        else:
            cred = credentials.ApplicationDefault()
            logger.info("Firebase initialised with Application Default Credentials.")

        firebase_admin.initialize_app(
            cred,
            {"projectId": settings.GOOGLE_CLOUD_PROJECT},
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Firebase initialisation failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _doc_to_dict(doc) -> Optional[Dict[str, Any]]:
    """Convert a Firestore DocumentSnapshot to a plain Python dict."""
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return data


def _now() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# FirestoreService
# ---------------------------------------------------------------------------


class FirestoreService:
    """
    Async-friendly wrapper around the synchronous Firestore Admin SDK.

    Usage
    -----
    Instantiate once at application startup and share the instance:

        fs = FirestoreService()
        doc = await fs.get_document("needs", "abc123")
    """

    def __init__(self) -> None:
        _init_firebase()
        self._db = firestore.client()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # Internal async executor helpers
    # ------------------------------------------------------------------

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    async def _run(self, fn, *args, **kwargs):
        """Run a blocking Firestore call in the default thread-pool."""
        loop = self._get_loop()
        return await loop.run_in_executor(None, partial(fn, *args, **kwargs))

    # ------------------------------------------------------------------
    # Generic CRUD
    # ------------------------------------------------------------------

    async def create_document(
        self,
        collection: str,
        data: Dict[str, Any],
        doc_id: Optional[str] = None,
    ) -> str:
        """
        Insert a new document into *collection*.

        Parameters
        ----------
        collection : str
            Firestore collection name.
        data : dict
            Document payload. ``created_at`` and ``updated_at`` are added
            automatically if not already present.
        doc_id : str, optional
            Use this as the document ID; if omitted Firestore auto-generates one.

        Returns
        -------
        str
            The document ID of the newly created document.
        """
        now = _now()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)

        def _create():
            col_ref = self._db.collection(collection)
            if doc_id:
                doc_ref = col_ref.document(doc_id)
                doc_ref.set(data)
                return doc_id
            _, doc_ref = col_ref.add(data)
            return doc_ref.id

        doc_id_result: str = await self._run(_create)
        logger.debug("Created document %s/%s", collection, doc_id_result)
        return doc_id_result

    async def get_document(
        self,
        collection: str,
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single document by ID.

        Returns ``None`` if the document does not exist.
        """

        def _get():
            return self._db.collection(collection).document(doc_id).get()

        doc = await self._run(_get)
        return _doc_to_dict(doc)

    async def update_document(
        self,
        collection: str,
        doc_id: str,
        data: Dict[str, Any],
    ) -> bool:
        """
        Merge-update an existing document.

        ``updated_at`` is always refreshed.

        Returns
        -------
        bool
            ``True`` on success, ``False`` if the document did not exist.
        """
        data["updated_at"] = _now()

        def _update():
            ref = self._db.collection(collection).document(doc_id)
            if not ref.get().exists:
                return False
            ref.update(data)
            return True

        result: bool = await self._run(_update)
        if result:
            logger.debug("Updated document %s/%s", collection, doc_id)
        else:
            logger.warning(
                "Update skipped – document %s/%s not found", collection, doc_id
            )
        return result

    async def set_document(
        self,
        collection: str,
        doc_id: str,
        data: Dict[str, Any],
        merge: bool = True,
    ) -> str:
        """
        Create or overwrite a document at the given *doc_id*.

        Parameters
        ----------
        merge : bool
            If ``True`` (default), fields not present in *data* are preserved.
            If ``False``, the document is fully replaced.
        """
        data.setdefault("created_at", _now())
        data["updated_at"] = _now()

        def _set():
            self._db.collection(collection).document(doc_id).set(data, merge=merge)

        await self._run(_set)
        return doc_id

    async def delete_document(
        self,
        collection: str,
        doc_id: str,
    ) -> bool:
        """
        Delete a document.

        Returns
        -------
        bool
            ``True`` if the document existed and was deleted, ``False`` otherwise.
        """

        def _delete():
            ref = self._db.collection(collection).document(doc_id)
            if not ref.get().exists:
                return False
            ref.delete()
            return True

        result: bool = await self._run(_delete)
        if result:
            logger.debug("Deleted document %s/%s", collection, doc_id)
        return result

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def query_collection(
        self,
        collection: str,
        filters: Optional[List[Tuple[str, str, Any]]] = None,
        order_by: Optional[str] = None,
        descending: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query a collection with optional filters and ordering.

        Parameters
        ----------
        filters : list of (field, operator, value) tuples, optional
            Examples::

                [("urgency", "==", "HIGH"), ("status", "==", "OPEN")]

            Supported operators: ``==``, ``!=``, ``<``, ``<=``, ``>``, ``>=``,
            ``in``, ``not-in``, ``array-contains``, ``array-contains-any``.
        order_by : str, optional
            Field name to sort by.
        descending : bool
            Sort direction (default ascending).
        limit : int
            Maximum number of documents to return (default 100, max 500).

        Returns
        -------
        list[dict]
            List of document dicts, each with an ``id`` key.
        """
        limit = min(limit, 500)

        def _query():
            ref = self._db.collection(collection)
            if filters:
                for field, op, value in filters:
                    ref = ref.where(filter=FieldFilter(field, op, value))
            if order_by:
                direction = (
                    firestore.Query.DESCENDING
                    if descending
                    else firestore.Query.ASCENDING
                )
                ref = ref.order_by(order_by, direction=direction)
            ref = ref.limit(limit)
            return ref.stream()

        docs = await self._run(_query)
        results = []
        for doc in docs:
            d = _doc_to_dict(doc)
            if d is not None:
                results.append(d)
        return results

    async def get_all_documents(
        self,
        collection: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return all documents in a collection (no filters)."""
        return await self.query_collection(collection, limit=limit)

    async def count_documents(
        self,
        collection: str,
        filters: Optional[List[Tuple[str, str, Any]]] = None,
    ) -> int:
        """Return the number of documents matching the given filters."""

        def _count():
            ref = self._db.collection(collection)
            if filters:
                for field, op, value in filters:
                    ref = ref.where(filter=FieldFilter(field, op, value))
            return ref.count().get()

        result = await self._run(_count)
        # result is a list of AggregationResult
        try:
            return result[0][0].value
        except (IndexError, AttributeError):
            return 0

    # ------------------------------------------------------------------
    # Domain-specific helpers
    # ------------------------------------------------------------------

    # ── Needs ─────────────────────────────────────────────────────────

    async def get_open_needs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return all needs with status == OPEN, ordered newest first."""
        return await self.query_collection(
            settings.COLLECTION_NEEDS,
            filters=[("status", "==", "OPEN")],
            order_by="created_at",
            descending=True,
            limit=limit,
        )

    async def get_needs_by_urgency(
        self, urgency: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Return open needs filtered by urgency level (HIGH / MEDIUM / LOW)."""
        return await self.query_collection(
            settings.COLLECTION_NEEDS,
            filters=[("urgency", "==", urgency), ("status", "==", "OPEN")],
            order_by="created_at",
            descending=True,
            limit=limit,
        )

    async def get_needs_by_category(
        self, category: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Return needs filtered by category."""
        return await self.query_collection(
            settings.COLLECTION_NEEDS,
            filters=[("category", "==", category)],
            order_by="created_at",
            descending=True,
            limit=limit,
        )

    # ── Volunteers ────────────────────────────────────────────────────

    async def get_available_volunteers(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Return all volunteers where availability == True."""
        return await self.query_collection(
            settings.COLLECTION_VOLUNTEERS,
            filters=[("availability", "==", True)],
            limit=limit,
        )

    async def get_volunteer_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """Look up a volunteer by their Firebase UID (document ID)."""
        return await self.get_document(settings.COLLECTION_VOLUNTEERS, uid)

    async def increment_volunteer_active_tasks(
        self, volunteer_id: str, delta: int = 1
    ) -> None:
        """Atomically increment (or decrement) the active_tasks counter."""

        def _increment():
            ref = self._db.collection(settings.COLLECTION_VOLUNTEERS).document(
                volunteer_id
            )
            ref.update(
                {
                    "active_tasks": firestore.Increment(delta),
                    "updated_at": _now(),
                }
            )

        await self._run(_increment)

    async def increment_volunteer_completed_tasks(self, volunteer_id: str) -> None:
        """Atomically increment tasks_completed and decrement active_tasks."""

        def _increment():
            ref = self._db.collection(settings.COLLECTION_VOLUNTEERS).document(
                volunteer_id
            )
            ref.update(
                {
                    "tasks_completed": firestore.Increment(1),
                    "active_tasks": firestore.Increment(-1),
                    "last_active_at": _now(),
                    "updated_at": _now(),
                }
            )

        await self._run(_increment)

    # ── Tasks ─────────────────────────────────────────────────────────

    async def get_tasks_by_volunteer(
        self, volunteer_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Return all tasks assigned to a specific volunteer."""
        return await self.query_collection(
            settings.COLLECTION_TASKS,
            filters=[("assigned_volunteer_id", "==", volunteer_id)],
            order_by="created_at",
            descending=True,
            limit=limit,
        )

    async def get_tasks_by_need(
        self, need_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Return all tasks linked to a specific need."""
        return await self.query_collection(
            settings.COLLECTION_TASKS,
            filters=[("need_id", "==", need_id)],
            order_by="created_at",
            descending=True,
            limit=limit,
        )

    async def get_tasks_by_status(
        self, status: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return tasks filtered by lifecycle status."""
        return await self.query_collection(
            settings.COLLECTION_TASKS,
            filters=[("status", "==", status)],
            order_by="updated_at",
            descending=True,
            limit=limit,
        )

    # ── Uploads ───────────────────────────────────────────────────────

    async def get_recent_uploads(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent upload records."""
        return await self.query_collection(
            settings.COLLECTION_UPLOADS,
            order_by="created_at",
            descending=True,
            limit=limit,
        )

    # ── Dashboard aggregation ─────────────────────────────────────────

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Aggregate dashboard statistics from Firestore.

        Returns a dict with:
        - needs_by_category   : { FOOD: N, HEALTH: N, … }
        - needs_by_urgency    : { HIGH: N, MEDIUM: N, LOW: N }
        - needs_by_status     : { OPEN: N, ASSIGNED: N, … }
        - tasks_by_status     : { PENDING: N, ASSIGNED: N, COMPLETED: N, … }
        - total_volunteers    : N
        - available_volunteers: N
        - recent_needs        : [last 10 NeedListItem dicts]
        - recent_tasks        : [last 10 TaskListItem dicts]
        """
        # Run all queries concurrently
        (
            all_needs,
            all_tasks,
            all_volunteers,
            available_volunteers,
            recent_needs,
            recent_tasks,
        ) = await asyncio.gather(
            self.get_all_documents(settings.COLLECTION_NEEDS, limit=500),
            self.get_all_documents(settings.COLLECTION_TASKS, limit=500),
            self.get_all_documents(settings.COLLECTION_VOLUNTEERS, limit=500),
            self.get_available_volunteers(limit=500),
            self.query_collection(
                settings.COLLECTION_NEEDS,
                order_by="created_at",
                descending=True,
                limit=10,
            ),
            self.query_collection(
                settings.COLLECTION_TASKS,
                order_by="created_at",
                descending=True,
                limit=10,
            ),
        )

        # ── Category breakdown ────────────────────────────────────────
        needs_by_category: Dict[str, int] = {}
        needs_by_urgency: Dict[str, int] = {}
        needs_by_status: Dict[str, int] = {}

        for need in all_needs:
            cat = need.get("category", "OTHER")
            urg = need.get("urgency", "LOW")
            sts = need.get("status", "OPEN")
            needs_by_category[cat] = needs_by_category.get(cat, 0) + 1
            needs_by_urgency[urg] = needs_by_urgency.get(urg, 0) + 1
            needs_by_status[sts] = needs_by_status.get(sts, 0) + 1

        # ── Task status breakdown ─────────────────────────────────────
        tasks_by_status: Dict[str, int] = {}
        for task in all_tasks:
            sts = task.get("status", "PENDING")
            tasks_by_status[sts] = tasks_by_status.get(sts, 0) + 1

        # ── Heatmap data (open needs with coordinates) ────────────────
        heatmap_points = [
            {
                "lat": n["latitude"],
                "lng": n["longitude"],
                "weight": 1.0
                if n.get("urgency") == "LOW"
                else 2.0
                if n.get("urgency") == "MEDIUM"
                else 3.0,
                "category": n.get("category", "OTHER"),
                "title": n.get("title", ""),
                "urgency": n.get("urgency", "LOW"),
            }
            for n in all_needs
            if n.get("latitude") and n.get("longitude") and n.get("status") == "OPEN"
        ]

        return {
            "needs_by_category": needs_by_category,
            "needs_by_urgency": needs_by_urgency,
            "needs_by_status": needs_by_status,
            "tasks_by_status": tasks_by_status,
            "total_needs": len(all_needs),
            "total_tasks": len(all_tasks),
            "total_volunteers": len(all_volunteers),
            "available_volunteers": len(available_volunteers),
            "recent_needs": recent_needs,
            "recent_tasks": recent_tasks,
            "heatmap_points": heatmap_points,
        }

    # ── User helpers ──────────────────────────────────────────────────

    async def get_user_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        return await self.get_document(settings.COLLECTION_USERS, uid)

    async def get_all_fcm_tokens(self, role: Optional[str] = None) -> List[str]:
        """
        Collect all non-null FCM tokens, optionally filtered by user role.
        """
        filters = [("fcm_token", "!=", None)]
        if role:
            filters.append(("role", "==", role))

        users = await self.query_collection(
            settings.COLLECTION_USERS,
            filters=filters,
            limit=500,
        )
        return [u["fcm_token"] for u in users if u.get("fcm_token")]

    # ── Uploads helpers ───────────────────────────────────────────────

    async def update_upload_status(
        self,
        upload_id: str,
        status: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update the processing status of an upload record."""
        data: Dict[str, Any] = {"status": status, "updated_at": _now()}
        if extra:
            data.update(extra)
        await self.update_document(settings.COLLECTION_UPLOADS, upload_id, data)
