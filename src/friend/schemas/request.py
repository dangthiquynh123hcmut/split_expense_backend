from typing import Literal, Optional
from uuid import UUID

from django.db.models import Q
from ninja import Field, FilterSchema, Schema

from authenticate.models import User
from utils.functions.remove_accents import remove_accents
from utils.schemas.fields import FilterField, OrderBySchema


class AddFriendRequest(Schema):
    receiver_uid: UUID
    message: Optional[str] = Field(..., max_length=255)


class FilterFriendSchema(FilterSchema):
    search: Optional[str] = FilterField(default=None, description="Search by full_name")

    def filter_search(self, value: Optional[str], current_user: User):
        if value is None:
            return Q()
        search_value = remove_accents(value)

        return Q(
            friend__full_name_no_accent__icontains=search_value, user=current_user
        ) | Q(user__full_name_no_accent__icontains=search_value, friend=current_user)


class OrderByUserSchema(OrderBySchema):
    order_by: Literal["updated_at", "full_name"] = "full_name"
