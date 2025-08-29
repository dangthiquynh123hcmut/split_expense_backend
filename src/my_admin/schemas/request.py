from ninja import FilterSchema

from utils.schemas.fields import FilterField


class UserFilter(FilterSchema):
    search: str = FilterField(
        None,
        q=[
            "phone_number__icontains",
            "email__icontains",
            "full_name__icontains",
        ],
        description="Search by phone_number, email, or full_name (using icontains)",
    )
