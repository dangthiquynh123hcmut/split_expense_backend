from typing import Literal, Optional
from uuid import UUID

from ninja import FilterSchema, Schema

from utils.schemas.fields import FilterField


class FilterLogApiSchema(FilterSchema):
    method_type: Optional[Literal["GET", "POST", "PUT", "DELETE", "PATCH"]] = None
    status_code: Optional[Literal["2xx", "4xx", "5xx"]] = None


class FilterContainer(FilterSchema):
    search: str = FilterField(
        None,
        q=[
            "user__full_name__icontains",
            "user__email__icontains",
            "log_message__icontains",
            "path__icontains",
        ],
        description="Exact match by user full_name, email, path or log_message (using icontains)",
    )


class CreateLogSchema(Schema):
    user: UUID
    path: str
    method_type: str
    status_code: int
    response_time: float
    log_message: str
