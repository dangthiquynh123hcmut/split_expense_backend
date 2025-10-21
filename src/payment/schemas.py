from typing import Optional

from ninja import Schema
from pydantic import Field


class PaymentRequest(Schema):
    amount: int
    bank_code: Optional[str] = None
    currency: Optional[str] = Field(..., description="USD or VND")


class PaymentResponse(Schema):
    payment_url: str
