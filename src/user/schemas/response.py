from datetime import datetime
from uuid import UUID

from ninja import Schema
from typing_extensions import Optional


class UserResponse(Schema):
    full_name: str
    avatar_url: Optional[str] = None
    uid: UUID


class SearchUserResponse(UserResponse):
    status: str | None = None
    date_joined: Optional[datetime] = None
