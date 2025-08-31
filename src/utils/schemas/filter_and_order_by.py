from typing import Literal, Optional

from django.db.models import Q
from ninja import FilterSchema

from utils.functions.remove_accents import remove_accents
from utils.schemas.fields import FilterField, OrderBySchema


class FilterFullNameSchema(FilterSchema):
    search: Optional[str] = FilterField(default=None, description="Search by full_name")

    def filter_search(self, value: Optional[str]):
        if value is None:
            return Q()
        return Q(user__full_name_no_accent__icontains=remove_accents(value))


class FilterNameSchema(FilterSchema):
    search: Optional[str] = FilterField(default=None, description="Search by name")

    def filter_search(self, value: Optional[str]):
        if value is None:
            return Q()
        return Q(name_no_accent__icontains=remove_accents(value))


class OrderByNameAndUpdatedAtSchema(OrderBySchema):
    order_by: Literal["updated_at", "name"] = "name"


class OrderByFullNameAndUpdatedAtSchema(OrderBySchema):
    order_by: Literal["updated_at", "full_name"] = "full_name"
