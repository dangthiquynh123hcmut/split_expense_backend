from datetime import datetime
from typing import List, Optional

from ninja import Schema
from pydantic import Field


class ReceiptItem(Schema):
    name: str = Field(..., description="Item name")
    quantity: Optional[float] = Field(default=1, description="Item quantity")
    unit_price: Optional[float] = Field(None, description="Price per unit")
    total_price: float = Field(..., description="Total price for this item")


class OCRReceiptResponse(Schema):
    items: List[ReceiptItem] = Field(
        default_factory=list, description="List of items purchased"
    )
    name: Optional[str] = Field(None, description="Suggested name for the expense")
    category: Optional[str] = Field(
        None, description="Suggested category for the expense"
    )
    total_amount: float = Field(..., description="Total amount paid")
    currency: Optional[str] = Field(None, description="Currency code (VND, USD, etc.)")
    note: Optional[str] = Field(None, description="Additional notes")
    expense_date: Optional[datetime] = Field(None, description="Date of purchase")
    end_date: Optional[datetime] = Field(
        None, description="End date for the expense period"
    )
