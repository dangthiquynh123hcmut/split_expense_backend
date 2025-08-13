from typing import Optional

from ninja import Field, Schema
from pydantic import ConfigDict


class UserSchema(Schema):
    avatar: Optional[str] = None
    email: str = Field(alias="username")
    full_name: Optional[str] = Field(alias="first_name")
    phone_number: Optional[str]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
