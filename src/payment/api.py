import json

from django.http import HttpRequest, JsonResponse

from payment.schemas import (
    PaymentRequest,
    PaymentResponse,
    PayOSCreateLinkRequest,
    PayOSCreateLinkResponse,
    PayOSPaymentInfoResponse,
)
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, get, post, put
from utils.router.permissions import IsAuthenticated
from utils.types import AuthenticatedRequest

from .exceptions import (
    PayOSCancelFailed,
    PayOSOrderNotFound,
    PayOSPaymentLinkCreationFailed,
)
from .payos_service import PayOSService
from .service import Service


@api(
    prefix_or_class="payment",
    tags=["Payment"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class PaymentAPI(Controller):
    def __init__(self):
        self.service = Service()

    @get("", response=PaymentResponse)
    def payment(self, request: AuthenticatedRequest, payload: PaymentRequest):
        return self.service.create_payment_url(request=request, payload=payload)

    @post("/deposit", response=bool)
    def create_deposit(self, request: AuthenticatedRequest, payload: PaymentRequest):
        self.service.create_deposit(
            user=request.user, amount=payload.amount, currency=payload.currency
        )
        return True


@api(
    prefix_or_class="payment/payos",
    tags=["PayOS"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class PayOSAPI(Controller):
    def __init__(self):
        self.service = PayOSService()

    @post(
        "/create-link",
        response=PayOSCreateLinkResponse,
        exceptions=(PayOSPaymentLinkCreationFailed,),
    )
    def create_payment_link(
        self, request: AuthenticatedRequest, payload: PayOSCreateLinkRequest
    ):
        return self.service.create_payment_link(user=request.user, payload=payload)

    @get(
        "/{order_code}",
        response=PayOSPaymentInfoResponse,
        exceptions=(PayOSOrderNotFound,),
    )
    def get_payment_info(self, request: AuthenticatedRequest, order_code: int):
        """Retrieve live payment status for an order belonging to the current user."""
        return self.service.get_payment_info(user=request.user, order_code=order_code)

    @put(
        "/{order_code}/cancel",
        response=bool,
        exceptions=(PayOSOrderNotFound, PayOSCancelFailed),
    )
    def cancel_payment(self, request: AuthenticatedRequest, order_code: int):
        """Cancel a pending PayOS payment link owned by the current user."""
        return self.service.cancel_payment(user=request.user, order_code=order_code)


@api(
    prefix_or_class="/payos/webhook",
    tags=["PayOS Webhook"],
    auth=None,
)
class PayOSWebhookAPI(Controller):
    def __init__(self):
        self.service = PayOSService()

    @post("")
    def handle_webhook(self, request: HttpRequest):
        """Receive and process a PayOS transfer webhook."""
        try:
            data = json.loads(request.body)
            self.service.handle_webhook(webhook_data=data)
            return JsonResponse({"error": 0, "message": "Ok", "data": None})
        except Exception as exc:
            return JsonResponse({"error": -1, "message": str(exc), "data": None})
