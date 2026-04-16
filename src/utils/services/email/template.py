from datetime import datetime

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from authenticate.models import Otp
from split_expense_system import settings
from utils.types import TUser


class EmailTemplate:
    def __init__(self):
        self._base_url = settings.FRONTEND_BASE_URL
        self._confirm_transfer_url = settings.URL_CONFIRM_TRANSFER

    def _sent_email(self, user: TUser, template_name: str, data: dict, subject: str):
        body = render_to_string(template_name, data)

        alternative = EmailMultiAlternatives(subject=subject, to=[user.email])
        alternative.attach_alternative(body, "text/html")

        return alternative

    def reset_password(self, user: TUser, otp: Otp):
        return self._sent_email(
            user=user,
            template_name="email/reset_password.html",
            data={
                "full_name": user.get_full_name(),
                "otp": otp.otp,
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

    def account_active(self, user: TUser, token: str):
        return self._sent_email(
            user=user,
            template_name="email/account_active.html",
            data={
                "reset_link": f"{self._base_url}?token={token}",
            },
            subject="Account active / kích hoạt tài khoản",
        )

    def confirm_transfer(
        self,
        to_user: TUser,
        from_name: str,
        amount: float,
        currency: str,
        group_name: str,
        description: str,
        confirm_token: str,
    ):
        confirm_link = (
            f"{self._confirm_transfer_url}/api/confirm-transfer?token={confirm_token}"
        )
        return self._sent_email(
            user=to_user,
            template_name="email/confirm_transfer.html",
            data={
                "to_name": to_user.get_full_name(),
                "from_name": from_name,
                "amount": amount,
                "currency": currency,
                "group_name": group_name,
                "description": description,
                "confirm_link": confirm_link,
            },
            subject="Xác nhận nhận tiền / Transfer confirmation",
        )
