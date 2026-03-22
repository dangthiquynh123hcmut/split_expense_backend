from typing import Any, Dict, List, Optional

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging


class FCMService:
    _instance = None

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
            return
        except ValueError:
            pass

        cred = credentials.Certificate(str(settings.FIREBASE_CREDENTIALS_PATH))
        firebase_admin.initialize_app(cred)

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

        message = messaging.MulticastMessage(
            tokens=device_tokens,
            notification=messaging.Notification(title=title, body=body, image=image),
            data={k: str(v) for k, v in (data or {}).items()},
        )
        return messaging.send_each_for_multicast(message)


# Create a singleton instance
fcm_service = FCMService()
