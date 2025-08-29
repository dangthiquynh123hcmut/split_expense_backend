from ninja import FilterSchema, Schema

from utils.schemas.fields import FilterField


class Request(Schema):
    name: str
    avatar_url: str


class UserFilterSchema(FilterSchema):
    search: str = FilterField(
        ...,
        q=[
            "phone_number__iexact",
            "email__iexact",
            "full_name__icontains",
        ],
        description="Exact match by email, phone_number and full_name (using icontains)",
    )
