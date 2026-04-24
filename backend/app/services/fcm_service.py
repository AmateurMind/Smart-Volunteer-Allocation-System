"""
SVAS Backend – Firebase Cloud Messaging (FCM) Service
Handles push notifications for task assignments, urgent alerts, and reminders.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import messaging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _firebase_ready() -> bool:
    """Return True if the Firebase Admin SDK has been initialised."""
    return bool(firebase_admin._apps)


def _stringify_data(data: Dict[str, Any]) -> Dict[str, str]:
    """
    FCM data payloads only accept string values.
    Convert every value in *data* to its string representation.
    """
    return {k: str(v) for k, v in (data or {}).items() if v is not None}


# ─────────────────────────────────────────────────────────────────────────────
# FCMService
# ─────────────────────────────────────────────────────────────────────────────


class FCMService:
    """
    Thin async-compatible wrapper around the Firebase Admin messaging SDK.

    All public methods are ``async`` and return a boolean indicating success.
    They never raise – failures are logged and ``False`` is returned so that
    notification errors never bubble up into the main request pipeline.

    Usage
    -----
    ::

        fcm = FCMService()
        ok = await fcm.send_notification(token, "Hello", "World")
    """

    # ------------------------------------------------------------------
    # Core send primitives
    # ------------------------------------------------------------------

    async def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None,
    ) -> bool:
        """
        Send a push notification to a single device FCM token.

        Parameters
        ----------
        token : str
            The recipient device's FCM registration token.
        title : str
            Notification title shown in the device notification tray.
        body : str
            Notification body text.
        data : dict, optional
            Arbitrary key-value payload delivered alongside the notification.
            All values are converted to strings automatically.
        image_url : str, optional
            URL of an image to display in the notification (Android / Web).

        Returns
        -------
        bool
            ``True`` if the message was accepted by FCM, ``False`` otherwise.
        """
        if not token or not token.strip():
            logger.warning("send_notification: empty FCM token – skipping.")
            return False

        if not _firebase_ready():
            logger.warning(
                "send_notification: Firebase not initialised – notification skipped."
            )
            return False

        try:
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url,
            )

            android_config = messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    icon="ic_notification",
                    color="#A47251",
                    sound="default",
                    image=image_url,
                ),
            )

            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(title=title, body=body),
                        sound="default",
                        badge=1,
                    )
                )
            )

            message = messaging.Message(
                token=token.strip(),
                notification=notification,
                android=android_config,
                apns=apns_config,
                data=_stringify_data(data or {}),
            )

            response = messaging.send(message)
            logger.info(
                "FCM notification sent. message_id=%s title='%s'", response, title
            )
            return True

        except messaging.UnregisteredError:
            logger.warning(
                "send_notification: token is unregistered (device uninstalled app)."
            )
            return False
        except messaging.SenderIdMismatchError:
            logger.error(
                "send_notification: sender ID mismatch – wrong Firebase project?"
            )
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("send_notification failed: %s", exc)
            return False

    async def send_multicast(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Send a notification to multiple device tokens at once.

        Uses FCM ``send_each_for_multicast`` which supports up to 500 tokens
        per call.  Tokens are batched automatically if the list is larger.

        Parameters
        ----------
        tokens : list[str]
            List of FCM registration tokens.
        title : str
            Notification title.
        body : str
            Notification body.
        data : dict, optional
            Arbitrary key-value data payload.
        image_url : str, optional
            Notification image URL.

        Returns
        -------
        dict
            ``{"success": N, "failure": M}`` counts.
        """
        if not tokens:
            logger.debug("send_multicast: empty token list – nothing to send.")
            return {"success": 0, "failure": 0}

        if not _firebase_ready():
            logger.warning(
                "send_multicast: Firebase not initialised – notifications skipped."
            )
            return {"success": 0, "failure": len(tokens)}

        # Deduplicate and clean tokens
        clean_tokens = list({t.strip() for t in tokens if t and t.strip()})

        success_count = 0
        failure_count = 0

        # FCM multicast limit is 500 tokens per request
        batch_size = 500
        for i in range(0, len(clean_tokens), batch_size):
            batch = clean_tokens[i : i + batch_size]
            try:
                message = messaging.MulticastMessage(
                    tokens=batch,
                    notification=messaging.Notification(
                        title=title, body=body, image=image_url
                    ),
                    android=messaging.AndroidConfig(
                        priority="high",
                        notification=messaging.AndroidNotification(
                            title=title,
                            body=body,
                            color="#A47251",
                            sound="default",
                        ),
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                alert=messaging.ApsAlert(title=title, body=body),
                                sound="default",
                            )
                        )
                    ),
                    data=_stringify_data(data or {}),
                )
                batch_response = messaging.send_each_for_multicast(message)
                success_count += batch_response.success_count
                failure_count += batch_response.failure_count

                if batch_response.failure_count:
                    for idx, resp in enumerate(batch_response.responses):
                        if not resp.success:
                            logger.debug(
                                "Multicast failure for token[%d]: %s",
                                i + idx,
                                resp.exception,
                            )

            except Exception as exc:  # noqa: BLE001
                logger.error("send_multicast batch error: %s", exc)
                failure_count += len(batch)

        logger.info(
            "send_multicast complete. success=%d failure=%d title='%s'",
            success_count,
            failure_count,
            title,
        )
        return {"success": success_count, "failure": failure_count}

    # ------------------------------------------------------------------
    # Domain-specific notification helpers
    # ------------------------------------------------------------------

    async def send_task_assignment(
        self,
        volunteer_token: str,
        task: Dict[str, Any],
    ) -> bool:
        """
        Notify a volunteer that a new task has been assigned to them.

        Parameters
        ----------
        volunteer_token : str
            FCM token of the assigned volunteer's device.
        task : dict
            Task document dict (must include ``title``, ``location``,
            ``urgency``, and optionally ``id``, ``due_date``).

        Returns
        -------
        bool
            ``True`` if the notification was sent successfully.
        """
        task_title = task.get("title", "New Task")
        location = task.get("location", "Unknown location")
        urgency = task.get("urgency", "MEDIUM")
        task_id = task.get("id", "")

        urgency_labels = {
            "HIGH": "🔴 URGENT",
            "MEDIUM": "🟡 Medium priority",
            "LOW": "🟢 Standard priority",
        }
        urgency_label = urgency_labels.get(urgency.upper(), urgency)

        title = "📋 New Task Assigned"
        body = f"{urgency_label} – {task_title} @ {location}"

        data = {
            "type": "TASK_ASSIGNED",
            "task_id": task_id,
            "urgency": urgency,
            "location": location,
            "category": task.get("category", ""),
            "need_id": task.get("need_id", ""),
        }

        return await self.send_notification(volunteer_token, title, body, data)

    async def send_urgent_alert(
        self,
        tokens: List[str],
        need: Dict[str, Any],
    ) -> Dict[str, int]:
        """
        Broadcast an urgent need alert to multiple coordinators / volunteers.

        Parameters
        ----------
        tokens : list[str]
            FCM tokens of all recipients.
        need : dict
            Need document dict (must include ``title``, ``location``,
            ``category``, and optionally ``beneficiary_count``, ``id``).

        Returns
        -------
        dict
            ``{"success": N, "failure": M}`` counts.
        """
        need_title = need.get("title", "Urgent Need")
        location = need.get("location", "Unknown location")
        category = need.get("category", "OTHER")
        beneficiaries = need.get("beneficiary_count")
        need_id = need.get("id", "")

        category_emojis = {
            "FOOD": "🍚",
            "HEALTH": "🏥",
            "EDUCATION": "📚",
            "SHELTER": "🏠",
            "CLOTHING": "👕",
            "OTHER": "📌",
        }
        emoji = category_emojis.get(category.upper(), "📌")

        title = f"🚨 Urgent {category.title()} Need Reported"

        body_parts = [f"{emoji} {need_title}", f"📍 {location}"]
        if beneficiaries:
            body_parts.append(f"👥 ~{beneficiaries} people affected")
        body = " • ".join(body_parts)

        data = {
            "type": "URGENT_ALERT",
            "need_id": need_id,
            "category": category,
            "urgency": "HIGH",
            "location": location,
        }

        return await self.send_multicast(tokens, title, body, data)

    async def send_reminder(
        self,
        volunteer_token: str,
        task: Dict[str, Any],
    ) -> bool:
        """
        Send a reminder to a volunteer about a pending or in-progress task.

        Parameters
        ----------
        volunteer_token : str
            FCM token of the volunteer's device.
        task : dict
            Task document dict.

        Returns
        -------
        bool
            ``True`` if the notification was sent successfully.
        """
        task_title = task.get("title", "Task")
        location = task.get("location", "")
        task_id = task.get("id", "")
        status = task.get("status", "ASSIGNED")
        due_date = task.get("due_date")

        if status == "ASSIGNED":
            title = "⏰ Task Reminder – Action Required"
            body = f"You have an unstarted task: {task_title}"
        elif status in ("ACCEPTED", "IN_PROGRESS"):
            title = "⏰ Task Reminder – In Progress"
            body = f"Don't forget to complete: {task_title}"
        else:
            title = "⏰ Task Reminder"
            body = f"Reminder about your task: {task_title}"

        if location:
            body += f" @ {location}"

        data = {
            "type": "TASK_REMINDER",
            "task_id": task_id,
            "status": status,
            "location": location,
            "due_date": str(due_date) if due_date else "",
        }

        return await self.send_notification(volunteer_token, title, body, data)

    async def send_task_status_update(
        self,
        coordinator_token: str,
        task: Dict[str, Any],
        new_status: str,
        volunteer_name: str = "A volunteer",
    ) -> bool:
        """
        Notify a coordinator when a volunteer updates a task's status.

        Parameters
        ----------
        coordinator_token : str
            FCM token of the coordinator's device.
        task : dict
            Task document dict.
        new_status : str
            The new task status (e.g. ``"COMPLETED"``).
        volunteer_name : str
            Display name of the volunteer who updated the status.

        Returns
        -------
        bool
            ``True`` if the notification was sent successfully.
        """
        task_title = task.get("title", "Task")
        task_id = task.get("id", "")

        status_messages = {
            "ACCEPTED": (
                "✅ Task Accepted",
                f"{volunteer_name} accepted '{task_title}'",
            ),
            "IN_PROGRESS": (
                "🔄 Task Started",
                f"{volunteer_name} started working on '{task_title}'",
            ),
            "COMPLETED": (
                "🎉 Task Completed",
                f"{volunteer_name} marked '{task_title}' as complete – please verify",
            ),
            "REJECTED": (
                "❌ Task Rejected",
                f"{volunteer_name} declined '{task_title}' – reassignment needed",
            ),
        }

        title, body = status_messages.get(
            new_status.upper(),
            (
                f"📋 Task {new_status.title()}",
                f"Task '{task_title}' status updated to {new_status}",
            ),
        )

        data = {
            "type": "TASK_STATUS_UPDATE",
            "task_id": task_id,
            "new_status": new_status,
            "need_id": task.get("need_id", ""),
        }

        return await self.send_notification(coordinator_token, title, body, data)

    async def send_welcome(
        self,
        volunteer_token: str,
        volunteer_name: str,
    ) -> bool:
        """
        Send a welcome notification to a newly registered volunteer.

        Parameters
        ----------
        volunteer_token : str
            FCM token of the volunteer's device.
        volunteer_name : str
            First name or full name of the volunteer.

        Returns
        -------
        bool
            ``True`` if the notification was sent successfully.
        """
        first_name = volunteer_name.split()[0] if volunteer_name else "there"
        title = "🌟 Welcome to SVAS!"
        body = (
            f"Hi {first_name}, you're now registered as a volunteer. "
            "You'll receive alerts when tasks matching your skills are available."
        )
        data = {"type": "WELCOME", "volunteer_name": volunteer_name}
        return await self.send_notification(volunteer_token, title, body, data)

    async def send_need_resolved(
        self,
        tokens: List[str],
        need: Dict[str, Any],
    ) -> Dict[str, int]:
        """
        Broadcast a 'need resolved' celebration message to all involved parties.

        Parameters
        ----------
        tokens : list[str]
            FCM tokens of volunteers and coordinators to notify.
        need : dict
            Resolved need document dict.

        Returns
        -------
        dict
            ``{"success": N, "failure": M}`` counts.
        """
        need_title = need.get("title", "Community Need")
        beneficiaries = need.get("beneficiary_count")

        title = "🎉 Need Successfully Resolved!"
        body = f"'{need_title}' has been resolved"
        if beneficiaries:
            body += f", helping ~{beneficiaries} people"
        body += ". Great work, team!"

        data = {
            "type": "NEED_RESOLVED",
            "need_id": need.get("id", ""),
            "category": need.get("category", "OTHER"),
        }

        return await self.send_multicast(tokens, title, body, data)
