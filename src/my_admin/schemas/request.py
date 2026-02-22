from typing import Literal, Optional
from uuid import UUID

from ninja import FilterSchema, Schema

from utils.schemas.fields import FilterField, OrderBySchema


class UserFilter(FilterSchema):
    search: str = FilterField(
        None,
        q=[
            "phone_number__icontains",
            "email__iexact",
            "full_name__icontains",
        ],
        description="Exact match by email and full_name or phone_number(using icontains)",
    )


class AdminCreateRequest(Schema):
    email: str


class FilterAdminSchema(FilterSchema):
    search: str = FilterField(
        None,
        q=[
            "email__icontains",
        ],
        description="Exact match by email (using icontains)",
    )


class OrderByBalanceSchema(OrderBySchema):
    order_by: Literal["balance", "full_name", "updated_at"] = "full_name"


class ActiveAdminRequest(Schema):
    password: str
    token: str


class FilterTransactionSchema(FilterSchema):
    search: Optional[str] = FilterField(
        None,
        q=[
            "user__full_name__icontains",
        ],
        description="Exact match by full_name (using icontains)",
    )
    type: Optional[Literal["withdraw", "deposit", "in_app"]] = None


class FilterNotificationSchema(FilterSchema):
    search: Optional[str] = FilterField(
        None,
        q=[
            "content__icontains",
        ],
        description="Exact match by content (using icontains)",
    )
    type: Optional[Literal["System", "Warning", "Announcement", "Reminder"]] = None


class CreateNotificationResquest(Schema):
    related_uid: Optional[UUID] = None
    content: str
    type: str
    to_user_uids: Optional[list[UUID]] = None
    is_broadcast: Optional[bool] = False
