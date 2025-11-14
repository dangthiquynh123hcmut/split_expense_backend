from typing import Dict, List, Optional

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
        """Initialize Firebase app with credentials from Django settings."""
        try:
            firebase_admin.get_app()
            return
        except ValueError:
            pass

        firebase_config = getattr(settings, "FIREBASE_CONFIG", {})
        cred = credentials.Certificate(firebase_config)
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
            response = messaging.send_multicast(message)
            return response
        except Exception:
            return None


# Create a singleton instance
fcm_service = FCMService()
