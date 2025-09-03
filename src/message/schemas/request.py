from typing import Optional

from django.db.models import Q
from ninja import FilterSchema, Schema

from utils.functions.remove_accents import remove_accents
from utils.schemas.fields import FilterField


class MessageIn(Schema):
    content: str


class MessageFilter(FilterSchema):
    search: Optional[str] = FilterField(default=None, description="Search by content")

    def filter_search(self, value: Optional[str]):
        if value is None:
            return Q()
        return Q(content__icontains=remove_accents(value))
