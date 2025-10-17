from datetime import datetime
from uuid import UUID

from ninja import Schema
from typing_extensions import Optional

from attachment.schemas.responses import AttachmentResponse


class UserResponse(Schema):
    full_name: str
    avatar_url: Optional[AttachmentResponse] = None
    uid: UUID


class SearchUserResponse(UserResponse):
    status: str | None = None
    date_joined: Optional[datetime] = None


class WalletResponse(Schema):
    balance: float
    user: UserResponse
    currency: str
