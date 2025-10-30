from payment.schemas import PaymentRequest, PaymentResponse
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, get, post
from utils.router.permissions import IsAuthenticated
from utils.types import AuthenticatedRequest

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
