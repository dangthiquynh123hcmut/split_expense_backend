from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from utils.types import TUser


class EmailTemplate:
    def __init__(self):
        self._base_url = settings.FRONTEND_URL

    def _sent_email(self, user: TUser, template_name: str, data: dict, subject: str):
        body = render_to_string(template_name, data)

        alternative = EmailMultiAlternatives(subject=subject, to=[user.email])
        alternative.attach_alternative(body, "text/html")

        return alternative

    def reset_password(self, user: TUser, token: str):
        return self._sent_email(
            user=user,
            template_name="email/reset_password.html",
            data={
                "full_name": user.get_full_name(),
                "reset_link": f"{self._base_url}/reset-password?token={token}",
            },
            subject="Forgot password / Quên mật khẩu",
        )

    def change_password(self, user: TUser):
        return self._sent_email(
            user=user,
            template_name="email/change_password.html",
            data={
                "full_name": user.get_full_name(),
                "formatted_time": datetime.now().strftime("%H:%M - %d/%m/%Y"),
            },
            subject="Change password / Thay đổi mật khẩu",
        )
