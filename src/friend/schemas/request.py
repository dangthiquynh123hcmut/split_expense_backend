from typing import Literal, Optional
from uuid import UUID

from django.db.models import Q
from ninja import Field, FilterSchema, Schema

from utils.functions.remove_accents import remove_accents
from utils.schemas.fields import FilterField, OrderBySchema


class AddFriendRequest(Schema):
    receiver_uid: UUID
    message: Optional[str] = Field(..., max_length=255)


class RespondFriendRequest(Schema):
    requester_uid: UUID
    action: Literal["ACCEPT", "REJECT"]


class FilterFriendSchema(FilterSchema):
    search: Optional[str] = FilterField(default=None)
    status: Optional[Literal["PENDING", "ACCEPTED"]] = FilterField(default=None)

    def filter_search(self, value: Optional[str]):
        if value is None:
            return Q()
        return Q(full_name_no_accent__icontains=remove_accents(value))


class OrderByUserSchema(OrderBySchema):
    order_by: Literal["updated_at"]
