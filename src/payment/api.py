from uuid import UUID

from django.conf import settings

from payment.schemas import PaymentRequest, PaymentResponse, UrlResponse
from utils.router.controller import Controller, api, get
from utils.router.permissions import IsAuthenticated
from utils.types import AuthenticatedRequest

from .service import Service


@api(
    prefix_or_class="payment",
    tags=["Payment"],
    auth=None,
    permissions=[IsAuthenticated],
)
class PaymentAPI(Controller):
    def __init__(self):
        self.service = Service()

    @get("", response=PaymentResponse, auth=True)
    def payment(self, request: AuthenticatedRequest, payload: PaymentRequest):
        return self.service.create_payment_url(request=request, payload=payload)

    @get("/ipn", response=UrlResponse)
    def vnpay_ipn(self, request):
        params = request.GET.dict()

        user_uid = UUID(params.get("vnp_OrderInfo", 0))
        amount = float(params.get("vnp_Amount", 0)) / 100
        currency = params.get("vnp_TxnRef")[-3:]
        self.service.process_ipn(user_uid=user_uid, amount=amount, currency=currency)
        return {"url": settings.RESPONSE_URL}
