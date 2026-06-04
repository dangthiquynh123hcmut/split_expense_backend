from typing import List

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from sendgrid_backend.mail import SendgridBackend

from ..base import BaseService


class EmailClient(BaseService):
    def __init__(
        self,
        api_key=None,
        sandbox_mode=False,
        echo_to_stdout=True,
    ):
        self._api_key = api_key or getattr(settings, "SENDGRID_API_KEY", None)
        if not self._api_key:
            self.logger.warning(
                "SENDGRID_API_KEY not configured; email will not be sent"
            )
            self._sender = None
            return

        self._sender = SendgridBackend(
            api_key=self._api_key,
            sandbox_mode_in_debug=sandbox_mode,
            echo_to_stdout=echo_to_stdout,
        )

    def send(self, messages: List[EmailMultiAlternatives]):
        if self._sender is None:
            self.logger.warning("Email sender not configured; skipping send")
            return
        try:
            self.logger.info("Sending email")
            self._sender.send_messages(messages)
            self.logger.info("Email sent successfully")
        except Exception as e:
            self.logger.error(e)
