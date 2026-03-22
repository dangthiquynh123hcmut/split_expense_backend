from payment.schemas import PayOSCreateLinkRequest
from utils.types import TUser

from .exceptions import PayOSOrderNotFound
from .models import PayOSOrder, PayOSOrderStatus


class PayOSQuery:
    @staticmethod
    def create_payment_link(
        user: TUser,
        payload: PayOSCreateLinkRequest,
        order_code: int,
        checkout_url: str,
        payment_link_id: str,
    ) -> None:
        PayOSOrder.objects.create(
            user=user,
            order_code=order_code,
            amount=payload.amount,
            currency=payload.currency,
            description=payload.description,
            checkout_url=checkout_url,
            payment_link_id=payment_link_id,
        )
        return

    @staticmethod
    def get_order_pending(order_code: int):

        try:
            return PayOSOrder.objects.get(
                order_code=order_code,
                status=PayOSOrderStatus.PENDING,
            )
        except PayOSOrder.DoesNotExist:
            return PayOSOrderNotFound()

    @staticmethod
    def get_payment_info_by_order_code(user: TUser, order_code: int) -> PayOSOrder:
        try:
            return PayOSOrder.objects.get(user=user, order_code=order_code)
        except PayOSOrder.DoesNotExist:
            raise PayOSOrderNotFound()

    @staticmethod
    def update_order_status(
        order: PayOSOrder, new_status: PayOSOrderStatus
    ) -> PayOSOrder:
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        return order
