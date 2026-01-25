from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import Schema

from attachment.schemas.responses import AttachmentResponse
from event.schemas.response import EventGroup
from group.schemas.response import GroupName
from utils.schemas.user import UserSchema


class AdminResponse(Schema):
    email: str
    uid: UUID
    status: str


class TodayOverviewResponse(Schema):
    total_users: int
    percent_increase_users: float
    percent_increase_transactions: float
    percent_increase_money: float
    percent_increase_new_users: float
    total_transactions: int
    new_users: int
    total_money: int


class UserInsightsResponse(Schema):
    month_year: str
    new_users: int
    loyal_users: int
    return_users: int


class ExpenseCategoryResponse(Schema):
    category: str
    total_amount: float


class RatingResponse(Schema):
    date: datetime
    rate: float


class GroupStatisticsResponse(Schema):
    total_groups: int
    total_members: int
    active_groups: int
    percent_increase_groups: float
    percent_increase_members: float
    percent_increase_active_groups: float


class EventManagementResponse(Schema):
    total_events: int
    total_members: int
    active_events: int
    total_finished_events: int
    percent_increase_events: float
    percent_increase_members: float
    percent_increase_active_events: float
    percent_increase_finished_events: float


class AdminGroupResponse(Schema):
    uid: UUID
    name: str
    status: str
    created_at: datetime
    total_members: int
    leader: UserSchema


class UserCreator(Schema):
    uid: UUID
    full_name: str
    avatar: Optional[AttachmentResponse] = None


class ListEventResponse(EventGroup):
    creator: UserCreator
    status: str
    group: GroupName


class UserEventSchema(UserCreator):
    email: str


class ListEventMemberResponse(Schema):
    event_member_uid: UUID
    user: UserEventSchema
    status: str
