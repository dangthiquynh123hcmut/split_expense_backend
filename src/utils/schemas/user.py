from typing import Optional

from ninja import Field, Schema


class UserSchema(Schema):
    avatar: Optional[str] 
    email: str
    full_name: Optional[str] 
    phone_number: Optional[str]
