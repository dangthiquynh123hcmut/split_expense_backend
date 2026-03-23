from typing import Optional

from ninja import Schema
from pydantic import ConfigDict, Field


class PaymentRequest(Schema):
    amount: int
    bank_code: Optional[str] = None
    currency: Optional[str] = Field(..., description="USD or VND")


class PaymentResponse(Schema):
    payment_url: str


class PayOSCreateLinkRequest(Schema):
    amount: int = Field(..., description="Payment amount in VND (integer, e.g. 10000)")
    description: Optional[str] = Field(
        None,
        max_length=25,
        description="Bank transfer note shown to the payer, max 25 characters",
    )
    currency: str = Field(default="VND", description="Currency code, e.g. VND")


class PayOSCreateLinkResponse(Schema):
    order_code: int
    qr_code: str
    payment_link_id: str


class PayOSPaymentInfoResponse(Schema):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    orderCode: int = 0
    amount: int = 0
    amountRemaining: int = 0
    status: str = ""
    transactions: list = Field(default_factory=list)
