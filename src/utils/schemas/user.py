from typing import Optional

from ninja import Schema

from attachment.schemas.responses import AttachmentResponse


class UserSchema(Schema):
    avatar_url: Optional[AttachmentResponse] = None
    email: str
    full_name: Optional[str]
    phone_number: Optional[str]
