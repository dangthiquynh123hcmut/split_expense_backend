import random
import time

from django.conf import settings
from django.db import transaction
from payos import PayOS
from payos.types import CreatePaymentLinkRequest, ItemData

from message.orm.notification_queries import NotificationORM
from user.queries import Query as UserQuery
from utils.enums import NotificationTypeEnum
from utils.services.firebase_cm.fcm_service import FCMService
from utils.types import TUser
from wallet.orm.deposit import DepositORM

from .exceptions import (
    PayOSCancelFailed,
    PayOSOrderNotFound,
    PayOSPaymentLinkCreationFailed,
    PayOSWebhookVerificationFailed,
)
from .models import PayOSOrderStatus
from .queries import PayOSQuery
from .schemas import PayOSCreateLinkRequest, PayOSCreateLinkResponse


_TEST_DESCRIPTIONS = {"Ma giao dich thu nghiem", "VQRIO123"}


class PayOSService:
    def __init__(self):
        self.user_query = UserQuery()
        self.deposit_orm = DepositORM()
        self.fcm_service = FCMService()
        self.notification_orm = NotificationORM()
        self.payos_client = PayOS(
            client_id=settings.PAYOS_CLIENT_ID,
            api_key=settings.PAYOS_API_KEY,
            checksum_key=settings.PAYOS_CHECKSUM_KEY,
        )
        self.payos_query = PayOSQuery()

    def create_payment_link(
        self, user: TUser, payload: PayOSCreateLinkRequest
    ) -> PayOSCreateLinkResponse:
        # create unique order code using current timestamp + random suffix to avoid collisions
        order_code = int(time.time()) * 1000 + random.randint(0, 999)
        item = ItemData(name=payload.item_name, quantity=1, price=payload.amount)
        payment_request = CreatePaymentLinkRequest(
            order_code=order_code,
            amount=payload.amount,
            description=payload.description,
            items=[item],
            cancel_url=settings.PAYOS_CANCEL_URL,
            return_url=settings.PAYOS_RETURN_URL,
            buyer_name=user.full_name,
        )

        try:
            response = self.payos_client.payment_requests.create(payment_request)
        except Exception as exc:
            raise PayOSPaymentLinkCreationFailed([str(exc)])
        self.payos_query.create_payment_link(
            user=user,
            payload=payload,
            order_code=order_code,
            checkout_url=response.checkout_url,
            payment_link_id=response.payment_link_id,
        )

        return PayOSCreateLinkResponse(
            order_code=order_code,
            checkout_url=response.checkout_url,
            payment_link_id=response.payment_link_id,
        )

    @transaction.atomic
    def handle_webhook(self, webhook_data: dict) -> None:
        """
        Verify a PayOS webhook payload, then credit the user's balance and
        record a WalletDeposit.  Idempotent: silently skips already-processed orders.
        """
        try:
            data = self.payos_client.verifyPaymentWebhookData(webhook_data)
        except Exception as exc:
            raise PayOSWebhookVerificationFailed([str(exc)])

        # PayOS sends test/confirmation webhooks — ignore them
        if data.description in _TEST_DESCRIPTIONS:
            return
        order = self.payos_query.get_order_pending(order_code=data.orderCode)
        if not order:
            return
        order = self.payos_query.update_order_status(
            order=order, new_status=PayOSOrderStatus.PAID
        )
        user = order.user
        amount = float(order.amount)
        currency = order.currency

        self.user_query.update_balance(user=user, amount=amount)
        deposit = self.deposit_orm.add_deposit_history(
            user=user, amount=amount, currency=currency
        )
        self.fcm_service.send_notification(
            token=user.fcm_token,
            title="Deposit successful",
            body=f"Your account has been topped up {amount:,.0f} {currency} via PayOS",
        )
        self.notification_orm.create_notification(
            from_user=user,
            related_uid=deposit.uid,
            content=f"You have deposited {amount:,.0f} {currency} via PayOS",
            type=NotificationTypeEnum.DEPOSIT,
            to_users=[user],
        )

    def get_payment_info(self, user: TUser, order_code: int) -> dict:
        self.payos_query.get_payment_info_by_order_code(
            user=user, order_code=order_code
        )

        try:
            info = self.payos_client.getPaymentLinkInformation(order_code)
        except Exception:
            raise PayOSOrderNotFound()

        return info.to_json()

    def cancel_payment(self, user: TUser, order_code: int) -> bool:
        order = self.payos_query.get_payment_info_by_order_code(
            user=user, order_code=order_code
        )

        if order.status != PayOSOrderStatus.PENDING:
            raise PayOSCancelFailed([f"Order is already {order.status}"])

        try:
            self.payos_client.cancelPaymentLink(order_code)
        except Exception as exc:
            raise PayOSCancelFailed([str(exc)])
        self.payos_query.update_order_status(
            order=order, new_status=PayOSOrderStatus.CANCELLED
        )
        return True
