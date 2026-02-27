from typing import Optional

from ninja import ModelSchema, Schema

from api_log.models import ApiLog
from user.schemas.response import UserResponse


class LogManagementResponse(Schema):
    total_errors: int
    percent_increase_errors: float
    today_errors: int
    percent_increase_today_errors: float
    avg_response_time: float
    percent_increase_avg_response_time: float


class LogResponse(ModelSchema):
    user: Optional[UserResponse] = None

    class Meta:
        model = ApiLog
        fields = "__all__"
