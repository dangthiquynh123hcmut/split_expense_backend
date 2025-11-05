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
    group_name: Optional[str] = FilterField(
        default=None, description="Search by group name"
    )
    group_id: Optional[UUID] = FilterField(
        default=None, description="Filter by group uid"
    )

    def get_filter_expression(self) -> Q:
        q = Q()
        if self.group_name:
            q &= Q(group__name=remove_accents(self.group_name))
        if self.group_id:
            q &= Q(group_id=self.group_id)
        return q


class FilterEventSchema(FilterSchema):
    event: Optional[str] = FilterField(default=None, description="Filter by event name")
    group: Optional[str] = FilterField(default=None, description="Filter by group name")
    category: Optional[str] = FilterField(
        default=None, description="Filter by category name"
    )


class FilterDateAndAmountSchema(FilterSchema):
    start: datetime = FilterField(
        default=None, description="Filter by created at, between start and end"
    )
    end: datetime = FilterField(
        default=None, description="Filter by created at, between start and end"
    )
    min_amount: Optional[float] = FilterField(
        default=None, description="Filter from min amount"
    )
    max_amount: Optional[float] = FilterField(
        default=None, description="Filter to max amount"
    )

    def get_filter_expression(self):
        q = Q()
        if self.start and self.end:
            q &= Q(created_at__gte=self.start, created_at__lte=self.end)
        if self.min_amount:
            q &= Q(amount__gte=self.min_amount)
        if self.max_amount:
            q &= Q(amount__lte=self.max_amount)
        return q


class FilterDateSchema(FilterSchema):
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


class FilterAmountSchema(FilterSchema):
    min_amount: Optional[float] = FilterField(
        default=None, description="Filter from min amount"
    )
    max_amount: Optional[float] = FilterField(
        default=None, description="Filter to max amount"
    )


class OrderByNameAndUpdatedAtSchema(OrderBySchema):
    order_by: Literal["updated_at", "name"] = "name"


class OrderByFullNameAndUpdatedAtSchema(OrderBySchema):
    order_by: Literal["updated_at", "full_name"] = "full_name"
