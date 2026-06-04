import logging
from typing import Any, Dict, List, Optional

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging


logger = logging.getLogger(__name__)


class FCMService:
    _instance = None
    _firebase_ready = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FCMService, cls).__new__(cls)
            cls._initialize_firebase()
        return cls._instance

    @classmethod
    def _initialize_firebase(cls):
        """Initialize Firebase app with credentials from service account JSON file."""
        try:
            firebase_admin.get_app()
            cls._firebase_ready = True
            return
        except ValueError:
            pass

        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        if not cred_path or not cred_path.exists():
            logger.warning(
                "FIREBASE_CREDENTIALS_PATH is missing or does not exist: %s; FCM disabled",
                cred_path,
            )
            return

        try:
            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred)
            cls._firebase_ready = True
        except Exception:
            logger.exception(
                "Failed to initialize Firebase with credentials at %s; FCM disabled",
                cred_path,
            )

    def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image: Optional[str] = None,
    ) -> str:
        """
        Send a notification to a device.
        """
        if not self._firebase_ready:
            logger.warning("Firebase not initialized; skipping send_notification")
            return "FCM not configured"

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body, image=image),
            token=token,
            data=data or {},
        )

        try:
            response = messaging.send(message)
            return response
        except Exception:
            return "Error sending FCM notification"

    def send_multicast_notification(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image: Optional[str] = None,
    ) -> messaging.BatchResponse:
        """
        Send a notification to multiple devices.
        Returns:
            BatchResponse: Response containing the results of the send operation
        """
        if not self._firebase_ready:
            logger.warning(
                "Firebase not initialized; skipping send_multicast_notification"
            )
            return None

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body, image=image),
            tokens=tokens,
            data=data or {},
        )

        try:
            response = messaging.send_each_for_multicast(message)
            return response
        except Exception:
            return None

    def send_chat_message_notification(
        self,
        device_tokens: List[str],
        title: str,
        body: str,
        data: Dict[str, Any] | None = None,
        image: Optional[str] | None = None,
    ):
        """Convenience wrapper to send chat notifications to multiple devices."""
        if not device_tokens:
            return None

        if not self._firebase_ready:
            logger.warning(
                "Firebase not initialized; skipping send_chat_message_notification"
            )
            return None

        message = messaging.MulticastMessage(
            tokens=device_tokens,
            notification=messaging.Notification(title=title, body=body, image=image),
            data={k: str(v) for k, v in (data or {}).items()},
        )
        return messaging.send_each_for_multicast(message)


# Create a singleton instance
fcm_service = FCMService()
