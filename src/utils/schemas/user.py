from typing import Optional

from ninja import Schema


class UserSchema(Schema):
    avatar: Optional[str] = None
    email: str
    full_name: Optional[str]
    phone_number: Optional[str]
