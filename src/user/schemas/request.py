from ninja import FilterSchema, Schema

from utils.schemas.fields import FilterField


class Request(Schema):
    name: str
    avatar_url: str


class UserFilterSchema(FilterSchema):
    search: str = FilterField(
        ...,
        q=[
            "phone_number__icontains",
            "email__icontains",
            "full_name__icontains",
        ],
        description="Search by phone_number, email, or full_name (using icontains)",
    )
