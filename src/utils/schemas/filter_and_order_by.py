from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

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


class FilterCurrencySchema(FilterSchema):
    currency: Optional[str] = FilterField(
        default=None, description="Filter by currency"
    )

    def filter_currency(self, value: Optional[str]):
        if value is None:
            return Q()
        return Q(currency__icontains=value)


class FilterNameSchema(FilterSchema):
    search: Optional[str] = FilterField(default=None, description="Search by name")

    def filter_search(self, value: Optional[str]):
        if value is None:
            return Q()
        return Q(name_no_accent__icontains=remove_accents(value))


class FilterGroupSchema(FilterSchema):
    search: Optional[str] = FilterField(
        default=None, description="Search by group name"
    )
    group_id: Optional[UUID] = FilterField(
        default=None, description="Filter by group uid"
    )

    def get_filter_q(self) -> Q:
        q = Q()
        if self.search:
            q &= Q(name__icontains=remove_accents(self.search))
        if self.group_id:
            q &= Q(group_id=self.group_id)
        return q


class FilterMonthSchema(FilterSchema):
    start: datetime = FilterField(
        default=None, description="Filter by created at, between start and end"
    )
    end: datetime = FilterField(
        default=None, description="Filter by created at, between start and end"
    )

    def get_filter_expression(self):
        q = Q()
        if self.start and self.end:
            q &= Q(created_at__gte=self.start, created_at__lte=self.end)
        return q


class OrderByNameAndUpdatedAtSchema(OrderBySchema):
    order_by: Literal["updated_at", "name"] = "name"


class OrderByFullNameAndUpdatedAtSchema(OrderBySchema):
    order_by: Literal["updated_at", "full_name"] = "full_name"
