"""
SVAS Backend – BigQuery Analytics Service
Handles event logging and analytical queries via the Google Cloud BigQuery SDK.
All database calls are offloaded to a thread-pool executor so they don't block
the FastAPI / asyncio event loop.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from functools import partial
from typing import Any, Dict, List, Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Optional import – BigQuery is not available in every environment
# ─────────────────────────────────────────────────────────────────────────────

try:
    from google.cloud import bigquery
    from google.cloud.exceptions import GoogleCloudError, NotFound

    _BQ_AVAILABLE = True
except ImportError:  # pragma: no cover
    bigquery = None  # type: ignore[assignment]
    NotFound = Exception  # type: ignore[assignment,misc]
    GoogleCloudError = Exception  # type: ignore[assignment,misc]
    _BQ_AVAILABLE = False
    logger.warning(
        "google-cloud-bigquery is not installed. "
        "BigQueryService will operate in no-op mode."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Table / schema definitions
# ─────────────────────────────────────────────────────────────────────────────

# Table IDs (relative to the configured dataset)
_TABLE_EVENTS = "events"
_TABLE_NEEDS = "need_snapshots"
_TABLE_VOLUNTEER_ACTIVITY = "volunteer_activity"

# BigQuery schema for the events table
_EVENTS_SCHEMA = [
    bigquery.SchemaField("event_id", "STRING", mode="REQUIRED")
    if _BQ_AVAILABLE
    else None,
    bigquery.SchemaField("event_type", "STRING", mode="REQUIRED")
    if _BQ_AVAILABLE
    else None,
    bigquery.SchemaField("event_timestamp", "TIMESTAMP", mode="REQUIRED")
    if _BQ_AVAILABLE
    else None,
    bigquery.SchemaField("user_uid", "STRING", mode="NULLABLE")
    if _BQ_AVAILABLE
    else None,
    bigquery.SchemaField("need_id", "STRING", mode="NULLABLE")
    if _BQ_AVAILABLE
    else None,
    bigquery.SchemaField("task_id", "STRING", mode="NULLABLE")
    if _BQ_AVAILABLE
    else None,
    bigquery.SchemaField("volunteer_id", "STRING", mode="NULLABLE")
    if _BQ_AVAILABLE
    else None,
    bigquery.SchemaField("category", "STRING", mode="NULLABLE")
    if _BQ_AVAILABLE
    else None,
    bigquery.SchemaField("urgency", "STRING", mode="NULLABLE")
    if _BQ_AVAILABLE
    else None,
    bigquery.SchemaField("location", "STRING", mode="NULLABLE")
    if _BQ_AVAILABLE
    else None,
    bigquery.SchemaField("metadata_json", "STRING", mode="NULLABLE")
    if _BQ_AVAILABLE
    else None,
]

# Only keep non-None entries (handles the _BQ_AVAILABLE=False case at module load)
_EVENTS_SCHEMA = [f for f in _EVENTS_SCHEMA if f is not None]

# ─────────────────────────────────────────────────────────────────────────────
# Recognised event types (used as constants to avoid typos)
# ─────────────────────────────────────────────────────────────────────────────


class EventType:
    # Data ingestion
    DATA_UPLOADED = "DATA_UPLOADED"
    DATA_ANALYZED = "DATA_ANALYZED"

    # Needs lifecycle
    NEED_CREATED = "NEED_CREATED"
    NEED_UPDATED = "NEED_UPDATED"
    NEED_RESOLVED = "NEED_RESOLVED"
    NEED_CLOSED = "NEED_CLOSED"

    # Volunteer events
    VOLUNTEER_REGISTERED = "VOLUNTEER_REGISTERED"
    VOLUNTEER_AVAILABILITY_CHANGED = "VOLUNTEER_AVAILABILITY_CHANGED"

    # Task lifecycle
    TASK_CREATED = "TASK_CREATED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_ACCEPTED = "TASK_ACCEPTED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_VERIFIED = "TASK_VERIFIED"
    TASK_CANCELLED = "TASK_CANCELLED"

    # AI matching
    MATCH_REQUESTED = "MATCH_REQUESTED"
    AUTO_ASSIGN_TRIGGERED = "AUTO_ASSIGN_TRIGGERED"

    # Notifications
    NOTIFICATION_SENT = "NOTIFICATION_SENT"
    URGENT_ALERT_SENT = "URGENT_ALERT_SENT"


# ─────────────────────────────────────────────────────────────────────────────
# BigQueryService
# ─────────────────────────────────────────────────────────────────────────────


class BigQueryService:
    """
    Analytics service backed by Google Cloud BigQuery.

    All write operations use streaming inserts (``insert_rows_json``) for
    low-latency event logging.  All read operations use parameterised SQL
    queries executed via the BigQuery client.

    When BigQuery is not configured or not reachable the service degrades
    gracefully: writes are silently dropped and reads return empty results,
    so the rest of the application continues to function normally.

    Usage
    -----
    ::

        bq = BigQueryService()
        await bq.log_event(EventType.NEED_CREATED, {"need_id": "abc", "category": "FOOD"})
        trends = await bq.get_need_trends(days=30)
    """

    def __init__(self) -> None:
        self._client: Optional[Any] = None  # google.cloud.bigquery.Client
        self._dataset_id: str = settings.BIGQUERY_DATASET
        self._project: str = settings.GOOGLE_CLOUD_PROJECT
        self._ready: bool = False
        self._init()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init(self) -> None:
        """
        Attempt to create a BigQuery client and ensure the dataset / tables
        exist.  Failures are logged as warnings; the service falls back to
        no-op mode rather than crashing the application.
        """
        if not _BQ_AVAILABLE:
            logger.warning("BigQueryService: SDK not installed – no-op mode active.")
            return

        try:
            self._client = bigquery.Client(project=self._project)
            self._ensure_dataset()
            self._ensure_events_table()
            self._ready = True
            logger.info(
                "BigQueryService initialised. Project=%s Dataset=%s",
                self._project,
                self._dataset_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "BigQueryService could not initialise (will use no-op mode): %s", exc
            )

    def _ensure_dataset(self) -> None:
        """Create the BigQuery dataset if it does not already exist."""
        dataset_ref = f"{self._project}.{self._dataset_id}"
        try:
            self._client.get_dataset(dataset_ref)
            logger.debug("BigQuery dataset '%s' already exists.", dataset_ref)
        except NotFound:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = settings.BIGQUERY_LOCATION
            dataset.description = (
                "SVAS analytics dataset – auto-created by the backend."
            )
            self._client.create_dataset(dataset, exists_ok=True)
            logger.info("Created BigQuery dataset '%s'.", dataset_ref)

    def _ensure_events_table(self) -> None:
        """Create the events table if it does not already exist."""
        if not _EVENTS_SCHEMA:
            return
        table_ref = f"{self._project}.{self._dataset_id}.{_TABLE_EVENTS}"
        try:
            self._client.get_table(table_ref)
            logger.debug("BigQuery table '%s' already exists.", table_ref)
        except NotFound:
            table = bigquery.Table(table_ref, schema=_EVENTS_SCHEMA)
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="event_timestamp",
            )
            self._client.create_table(table, exists_ok=True)
            logger.info("Created BigQuery events table '%s'.", table_ref)

    # ------------------------------------------------------------------
    # Internal async executor
    # ------------------------------------------------------------------

    async def _run(self, fn, *args, **kwargs) -> Any:
        """Run a blocking BigQuery SDK call in the default thread-pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(fn, *args, **kwargs))

    # ------------------------------------------------------------------
    # Event logging (write)
    # ------------------------------------------------------------------

    async def log_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> bool:
        """
        Stream a single analytics event into the BigQuery events table.

        Parameters
        ----------
        event_type : str
            One of the ``EventType`` class constants, e.g.
            ``EventType.NEED_CREATED``.
        event_data : dict
            Arbitrary key/value pairs associated with the event.
            Well-known keys that map to dedicated columns:
            ``user_uid``, ``need_id``, ``task_id``, ``volunteer_id``,
            ``category``, ``urgency``, ``location``.
            All remaining keys are serialised into ``metadata_json``.

        Returns
        -------
        bool
            ``True`` if the row was successfully inserted, ``False`` otherwise.
        """
        if not self._ready or self._client is None:
            logger.debug(
                "BigQueryService not ready – skipping event log: %s", event_type
            )
            return False

        import json

        # Split known columns from the rest (→ metadata_json)
        known_keys = {
            "user_uid",
            "need_id",
            "task_id",
            "volunteer_id",
            "category",
            "urgency",
            "location",
        }
        metadata = {k: v for k, v in event_data.items() if k not in known_keys}

        row = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "event_timestamp": datetime.utcnow().isoformat() + "Z",
            "user_uid": event_data.get("user_uid"),
            "need_id": event_data.get("need_id"),
            "task_id": event_data.get("task_id"),
            "volunteer_id": event_data.get("volunteer_id"),
            "category": event_data.get("category"),
            "urgency": event_data.get("urgency"),
            "location": event_data.get("location"),
            "metadata_json": json.dumps(metadata, default=str) if metadata else None,
        }

        table_ref = f"{self._project}.{self._dataset_id}.{_TABLE_EVENTS}"

        def _insert():
            errors = self._client.insert_rows_json(table_ref, [row])
            return errors

        try:
            errors = await self._run(_insert)
            if errors:
                logger.warning(
                    "BigQuery insert_rows_json returned errors for event '%s': %s",
                    event_type,
                    errors,
                )
                return False
            logger.debug("BigQuery event logged: %s", event_type)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("BigQuery log_event failed: %s", exc)
            return False

    async def log_events_batch(
        self,
        events: List[Dict[str, Any]],
    ) -> bool:
        """
        Stream multiple events in a single BigQuery insert call.

        Parameters
        ----------
        events : list[dict]
            Each dict must have an ``event_type`` key plus the same optional
            keys as :meth:`log_event`.

        Returns
        -------
        bool
            ``True`` if all rows were inserted without errors.
        """
        if not self._ready or self._client is None:
            return False

        import json

        known_keys = {
            "event_type",
            "user_uid",
            "need_id",
            "task_id",
            "volunteer_id",
            "category",
            "urgency",
            "location",
        }

        rows = []
        for ev in events:
            metadata = {k: v for k, v in ev.items() if k not in known_keys}
            rows.append(
                {
                    "event_id": str(uuid.uuid4()),
                    "event_type": ev.get("event_type", "UNKNOWN"),
                    "event_timestamp": datetime.utcnow().isoformat() + "Z",
                    "user_uid": ev.get("user_uid"),
                    "need_id": ev.get("need_id"),
                    "task_id": ev.get("task_id"),
                    "volunteer_id": ev.get("volunteer_id"),
                    "category": ev.get("category"),
                    "urgency": ev.get("urgency"),
                    "location": ev.get("location"),
                    "metadata_json": json.dumps(metadata, default=str)
                    if metadata
                    else None,
                }
            )

        table_ref = f"{self._project}.{self._dataset_id}.{_TABLE_EVENTS}"

        def _insert():
            return self._client.insert_rows_json(table_ref, rows)

        try:
            errors = await self._run(_insert)
            if errors:
                logger.warning("BigQuery batch insert errors: %s", errors)
                return False
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("BigQuery log_events_batch failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Analytical queries (read)
    # ------------------------------------------------------------------

    async def _query(
        self, sql: str, params: Optional[List[Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a parameterised BigQuery SQL query and return the results as
        a list of plain Python dicts.

        Falls back to an empty list if BigQuery is unavailable.
        """
        if not self._ready or self._client is None:
            logger.debug("BigQueryService not ready – returning empty query result.")
            return []

        def _run_query():
            job_config = bigquery.QueryJobConfig(query_parameters=params or [])
            job = self._client.query(sql, job_config=job_config)
            results = job.result()  # blocks until complete
            return [dict(row) for row in results]

        try:
            return await self._run(_run_query)
        except Exception as exc:  # noqa: BLE001
            logger.error("BigQuery query failed.\nSQL: %s\nError: %s", sql, exc)
            return []

    async def get_need_trends(
        self,
        days: int = 30,
        project: Optional[str] = None,
        dataset: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return daily counts of NEED_CREATED events grouped by category for the
        last ``days`` days.

        Parameters
        ----------
        days : int
            Look-back window in days (default 30).

        Returns
        -------
        list[dict]
            Rows with keys: ``date`` (str YYYY-MM-DD), ``category`` (str),
            ``count`` (int).
        """
        proj = project or self._project
        ds = dataset or self._dataset_id

        sql = f"""
            SELECT
                DATE(event_timestamp) AS date,
                category,
                COUNT(*) AS count
            FROM `{proj}.{ds}.{_TABLE_EVENTS}`
            WHERE
                event_type = @event_type
                AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
                AND category IS NOT NULL
            GROUP BY
                date, category
            ORDER BY
                date DESC, count DESC
        """

        params = [
            bigquery.ScalarQueryParameter(
                "event_type", "STRING", EventType.NEED_CREATED
            ),
            bigquery.ScalarQueryParameter("days", "INT64", days),
        ]

        results = await self._query(sql, params)
        # Ensure date is serialised as a string
        for row in results:
            if hasattr(row.get("date"), "isoformat"):
                row["date"] = row["date"].isoformat()
        return results

    async def get_volunteer_performance(
        self,
        volunteer_id: Optional[str] = None,
        days: int = 90,
    ) -> List[Dict[str, Any]]:
        """
        Return task-completion counts per volunteer (or for a single volunteer).

        Parameters
        ----------
        volunteer_id : str, optional
            If provided, filter to a single volunteer.
        days : int
            Look-back window (default 90 days).

        Returns
        -------
        list[dict]
            Rows with keys: ``volunteer_id``, ``tasks_completed``,
            ``tasks_assigned``, ``completion_rate`` (float 0–1).
        """
        proj = self._project
        ds = self._dataset_id

        volunteer_filter = "AND volunteer_id = @volunteer_id" if volunteer_id else ""

        sql = f"""
            SELECT
                volunteer_id,
                COUNTIF(event_type = @completed_type) AS tasks_completed,
                COUNTIF(event_type = @assigned_type)  AS tasks_assigned,
                SAFE_DIVIDE(
                    COUNTIF(event_type = @completed_type),
                    NULLIF(COUNTIF(event_type = @assigned_type), 0)
                ) AS completion_rate
            FROM `{proj}.{ds}.{_TABLE_EVENTS}`
            WHERE
                volunteer_id IS NOT NULL
                AND event_type IN (@completed_type, @assigned_type)
                AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
                {volunteer_filter}
            GROUP BY volunteer_id
            ORDER BY tasks_completed DESC
            LIMIT 50
        """

        params = [
            bigquery.ScalarQueryParameter(
                "completed_type", "STRING", EventType.TASK_COMPLETED
            ),
            bigquery.ScalarQueryParameter(
                "assigned_type", "STRING", EventType.TASK_ASSIGNED
            ),
            bigquery.ScalarQueryParameter("days", "INT64", days),
        ]
        if volunteer_id:
            params.append(
                bigquery.ScalarQueryParameter("volunteer_id", "STRING", volunteer_id)
            )

        return await self._query(sql, params)

    async def get_completion_rates(self, days: int = 30) -> Dict[str, Any]:
        """
        Compute overall task completion statistics.

        Returns
        -------
        dict
            Keys: ``total_assigned``, ``total_completed``, ``total_cancelled``,
            ``completion_rate`` (float), ``cancellation_rate`` (float),
            ``period_days`` (int).
        """
        proj = self._project
        ds = self._dataset_id

        sql = f"""
            SELECT
                COUNTIF(event_type = @assigned)   AS total_assigned,
                COUNTIF(event_type = @completed)  AS total_completed,
                COUNTIF(event_type = @cancelled)  AS total_cancelled
            FROM `{proj}.{ds}.{_TABLE_EVENTS}`
            WHERE
                event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
                AND event_type IN (@assigned, @completed, @cancelled)
        """

        params = [
            bigquery.ScalarQueryParameter(
                "assigned", "STRING", EventType.TASK_ASSIGNED
            ),
            bigquery.ScalarQueryParameter(
                "completed", "STRING", EventType.TASK_COMPLETED
            ),
            bigquery.ScalarQueryParameter(
                "cancelled", "STRING", EventType.TASK_CANCELLED
            ),
            bigquery.ScalarQueryParameter("days", "INT64", days),
        ]

        rows = await self._query(sql, params)

        if not rows:
            return {
                "total_assigned": 0,
                "total_completed": 0,
                "total_cancelled": 0,
                "completion_rate": 0.0,
                "cancellation_rate": 0.0,
                "period_days": days,
            }

        row = rows[0]
        total_assigned = int(row.get("total_assigned") or 0)
        total_completed = int(row.get("total_completed") or 0)
        total_cancelled = int(row.get("total_cancelled") or 0)

        completion_rate = (
            round(total_completed / total_assigned, 4) if total_assigned > 0 else 0.0
        )
        cancellation_rate = (
            round(total_cancelled / total_assigned, 4) if total_assigned > 0 else 0.0
        )

        return {
            "total_assigned": total_assigned,
            "total_completed": total_completed,
            "total_cancelled": total_cancelled,
            "completion_rate": completion_rate,
            "cancellation_rate": cancellation_rate,
            "period_days": days,
        }

    async def get_category_breakdown(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Return the count of needs created, grouped by category, for the last
        ``days`` days.

        Returns
        -------
        list[dict]
            Rows with keys: ``category`` (str), ``count`` (int),
            ``high_urgency`` (int), ``medium_urgency`` (int), ``low_urgency`` (int).
        """
        proj = self._project
        ds = self._dataset_id

        sql = f"""
            SELECT
                category,
                COUNT(*) AS count,
                COUNTIF(urgency = 'HIGH')   AS high_urgency,
                COUNTIF(urgency = 'MEDIUM') AS medium_urgency,
                COUNTIF(urgency = 'LOW')    AS low_urgency
            FROM `{proj}.{ds}.{_TABLE_EVENTS}`
            WHERE
                event_type = @event_type
                AND category IS NOT NULL
                AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
            GROUP BY category
            ORDER BY count DESC
        """

        params = [
            bigquery.ScalarQueryParameter(
                "event_type", "STRING", EventType.NEED_CREATED
            ),
            bigquery.ScalarQueryParameter("days", "INT64", days),
        ]

        return await self._query(sql, params)

    async def get_daily_activity(self, days: int = 14) -> List[Dict[str, Any]]:
        """
        Return a day-by-day breakdown of key event counts.

        Returns
        -------
        list[dict]
            Rows with keys: ``date``, ``needs_created``, ``tasks_assigned``,
            ``tasks_completed``, ``volunteers_registered``.
        """
        proj = self._project
        ds = self._dataset_id

        sql = f"""
            SELECT
                DATE(event_timestamp) AS date,
                COUNTIF(event_type = @need_created)    AS needs_created,
                COUNTIF(event_type = @task_assigned)   AS tasks_assigned,
                COUNTIF(event_type = @task_completed)  AS tasks_completed,
                COUNTIF(event_type = @vol_registered)  AS volunteers_registered
            FROM `{proj}.{ds}.{_TABLE_EVENTS}`
            WHERE
                event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
            GROUP BY date
            ORDER BY date DESC
        """

        params = [
            bigquery.ScalarQueryParameter(
                "need_created", "STRING", EventType.NEED_CREATED
            ),
            bigquery.ScalarQueryParameter(
                "task_assigned", "STRING", EventType.TASK_ASSIGNED
            ),
            bigquery.ScalarQueryParameter(
                "task_completed", "STRING", EventType.TASK_COMPLETED
            ),
            bigquery.ScalarQueryParameter(
                "vol_registered", "STRING", EventType.VOLUNTEER_REGISTERED
            ),
            bigquery.ScalarQueryParameter("days", "INT64", days),
        ]

        results = await self._query(sql, params)
        for row in results:
            if hasattr(row.get("date"), "isoformat"):
                row["date"] = row["date"].isoformat()
        return results

    async def get_response_time_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Compute average time (in hours) between need creation and first task
        assignment, segmented by urgency level.

        Returns
        -------
        dict
            Keys: ``HIGH``, ``MEDIUM``, ``LOW`` – each with an
            ``avg_hours_to_assign`` float, plus an ``overall`` aggregate.
        """
        proj = self._project
        ds = self._dataset_id

        sql = f"""
            WITH created AS (
                SELECT need_id, urgency, event_timestamp AS created_ts
                FROM `{proj}.{ds}.{_TABLE_EVENTS}`
                WHERE event_type = @need_created
                  AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
            ),
            assigned AS (
                SELECT need_id, MIN(event_timestamp) AS assigned_ts
                FROM `{proj}.{ds}.{_TABLE_EVENTS}`
                WHERE event_type = @task_assigned
                GROUP BY need_id
            )
            SELECT
                c.urgency,
                AVG(
                    TIMESTAMP_DIFF(a.assigned_ts, c.created_ts, MINUTE) / 60.0
                ) AS avg_hours_to_assign,
                COUNT(*) AS sample_size
            FROM created c
            JOIN assigned a USING (need_id)
            WHERE a.assigned_ts > c.created_ts
            GROUP BY c.urgency
        """

        params = [
            bigquery.ScalarQueryParameter(
                "need_created", "STRING", EventType.NEED_CREATED
            ),
            bigquery.ScalarQueryParameter(
                "task_assigned", "STRING", EventType.TASK_ASSIGNED
            ),
            bigquery.ScalarQueryParameter("days", "INT64", days),
        ]

        rows = await self._query(sql, params)

        result: Dict[str, Any] = {
            "HIGH": {"avg_hours_to_assign": None, "sample_size": 0},
            "MEDIUM": {"avg_hours_to_assign": None, "sample_size": 0},
            "LOW": {"avg_hours_to_assign": None, "sample_size": 0},
            "overall": {"avg_hours_to_assign": None, "sample_size": 0},
            "period_days": days,
        }

        total_hours = 0.0
        total_samples = 0

        for row in rows:
            urgency = (row.get("urgency") or "OTHER").upper()
            avg_h = float(row.get("avg_hours_to_assign") or 0)
            samples = int(row.get("sample_size") or 0)

            if urgency in result:
                result[urgency] = {
                    "avg_hours_to_assign": round(avg_h, 2),
                    "sample_size": samples,
                }
            total_hours += avg_h * samples
            total_samples += samples

        if total_samples > 0:
            result["overall"] = {
                "avg_hours_to_assign": round(total_hours / total_samples, 2),
                "sample_size": total_samples,
            }

        return result

    async def get_top_locations(
        self, days: int = 30, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Return the locations with the most open needs in the given period.

        Returns
        -------
        list[dict]
            Rows with keys: ``location`` (str), ``count`` (int).
        """
        proj = self._project
        ds = self._dataset_id

        sql = f"""
            SELECT
                location,
                COUNT(*) AS count
            FROM `{proj}.{ds}.{_TABLE_EVENTS}`
            WHERE
                event_type = @event_type
                AND location IS NOT NULL
                AND TRIM(location) != ''
                AND event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
            GROUP BY location
            ORDER BY count DESC
            LIMIT @lim
        """

        params = [
            bigquery.ScalarQueryParameter(
                "event_type", "STRING", EventType.NEED_CREATED
            ),
            bigquery.ScalarQueryParameter("days", "INT64", days),
            bigquery.ScalarQueryParameter("lim", "INT64", limit),
        ]

        return await self._query(sql, params)

    async def get_ngo_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        High-level NGO performance summary for the reporting dashboard.

        Returns
        -------
        dict
            Aggregated KPIs: ``total_needs_registered``,
            ``needs_resolved``, ``resolution_rate``,
            ``avg_volunteers_per_task``, ``period_days``.
        """
        proj = self._project
        ds = self._dataset_id

        sql = f"""
            SELECT
                COUNTIF(event_type = @need_created)  AS total_needs_registered,
                COUNTIF(event_type = @need_resolved) AS needs_resolved,
                COUNTIF(event_type = @task_assigned) AS tasks_assigned,
                COUNT(DISTINCT CASE WHEN event_type = @task_assigned THEN volunteer_id END)
                    AS unique_volunteers_deployed
            FROM `{proj}.{ds}.{_TABLE_EVENTS}`
            WHERE
                event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
        """

        params = [
            bigquery.ScalarQueryParameter(
                "need_created", "STRING", EventType.NEED_CREATED
            ),
            bigquery.ScalarQueryParameter(
                "need_resolved", "STRING", EventType.NEED_RESOLVED
            ),
            bigquery.ScalarQueryParameter(
                "task_assigned", "STRING", EventType.TASK_ASSIGNED
            ),
            bigquery.ScalarQueryParameter("days", "INT64", days),
        ]

        rows = await self._query(sql, params)
        if not rows:
            return {
                "total_needs_registered": 0,
                "needs_resolved": 0,
                "resolution_rate": 0.0,
                "tasks_assigned": 0,
                "unique_volunteers_deployed": 0,
                "period_days": days,
            }

        row = rows[0]
        total = int(row.get("total_needs_registered") or 0)
        resolved = int(row.get("needs_resolved") or 0)

        return {
            "total_needs_registered": total,
            "needs_resolved": resolved,
            "resolution_rate": round(resolved / total, 4) if total > 0 else 0.0,
            "tasks_assigned": int(row.get("tasks_assigned") or 0),
            "unique_volunteers_deployed": int(
                row.get("unique_volunteers_deployed") or 0
            ),
            "period_days": days,
        }

    # ------------------------------------------------------------------
    # Health / status
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """Return ``True`` if the BigQuery client is initialised and ready."""
        return self._ready

    async def health_check(self) -> Dict[str, Any]:
        """
        Run a lightweight query to verify BigQuery connectivity.

        Returns
        -------
        dict
            ``{"status": "ok", "latency_ms": float}``  or
            ``{"status": "unavailable", "error": str}``.
        """
        if not self._ready:
            return {"status": "unavailable", "error": "Client not initialised"}

        import time

        sql = "SELECT 1 AS ping"
        start = time.perf_counter()
        try:
            rows = await self._query(sql)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            if rows and rows[0].get("ping") == 1:
                return {"status": "ok", "latency_ms": latency_ms}
            return {"status": "unexpected_response", "rows": rows}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc)}
