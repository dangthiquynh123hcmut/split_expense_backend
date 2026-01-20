from ninja import FilterSchema, Schema

from utils.schemas.fields import FilterField


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
