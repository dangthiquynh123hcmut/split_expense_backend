from typing import Optional
from uuid import UUID

from ninja import ModelSchema, Schema

from api_log.models import ApiLog
from attachment.schemas.responses import AttachmentResponse


class LogManagementResponse(Schema):
    total_errors: int
    percent_increase_errors: float
    today_errors: int
    percent_increase_today_errors: float
    avg_response_time: float
    percent_increase_avg_response_time: float


class LogUserResponse(Schema):
    full_name: Optional[str] = None
    email: str
    balance: float
    avatar_url: Optional[AttachmentResponse] = None
    uid: UUID


class LogResponse(ModelSchema):
    user: Optional[LogUserResponse] = None

    class Meta:
        model = ApiLog
        fields = "__all__"
