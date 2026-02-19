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
    avatar: Optional[AttachmentResponse] = None


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
    user_infor: UserEventSchema
    status: str


class ExpenseManagementResponse(Schema):
    total_expenses: int
    total_avg_amount: float
    active_expenses: int
    total_expired_expenses: int
    percent_increase_expenses: float
    percent_increase_avg_amount: float
    percent_increase_active_expenses: float
    percent_increase_expired_expenses: float


class NameEvent(Schema):
    uid: UUID
    name: str


class ExpenseItemResponse(Schema):
    name: str
    status: str
    category: str
    total_amount: float
    currency: str
    expense_date: datetime
    paid_by: UserEventSchema
    creator: UserEventSchema
    event: NameEvent
    split_type: str
    uid: UUID
    note: Optional[str] = None


class ExpenseInEventResponse(Schema):
    total_amount: float
    expenses: Optional[list[ExpenseItemResponse]] = None


class UserSharesInExpenseResponse(Schema):
    user: UserEventSchema
    amount: float


class SplitExpenseResponse(Schema):
    total_amount: float
    currency: str
    split_type: str
    list_user_shares: Optional[list[UserSharesInExpenseResponse]] = None


class ExpenseAttachmentResponse(AttachmentResponse):
    size: int
    created_at: datetime


class MessageManagementResponse(Schema):
    total_messages: int
    active_groups: int
    message_today: int
    attachments: int
    percent_increase_messages: float
    percent_increase_active_groups: float
    percent_increase_message_today: float
    percent_increase_attachments: float


class MessageGroupResponse(Schema):
    uid: UUID
    group_name: str
    total_members: int
    total_messages: int
    total_messages_unread: int
    last_message: Optional[datetime] = None
    last_message_content: Optional[str] = None


class MessageItemResponse(Schema):
    uid: UUID
    sender: UserCreator
    content: str
    created_at: datetime
    status: str
    attachments: Optional[list[AttachmentResponse]] = None


class MessageInGroupResponse(Schema):
    name: str
    total_members: int
    total_messages: int
    messages: Optional[list[MessageItemResponse]] = None
    avatar_url: Optional[AttachmentResponse] = None


class UserInforResponse(UserSchema):
    status: bool
    joined: datetime
    role: str
    total_expenses: float
    total_groups: int
    last_login: Optional[datetime] = None
    total_balance: float


class ParticipatingGroupsResponse(Schema):
    group_uid: UUID
    group_name: str
    role: str
    joined_at: datetime


class ListExpenseResponse(Schema):
    expense_uid: UUID
    name: str
    amount: float
    currency: str
    expense_date: datetime
    end_date: Optional[datetime] = None


class TransactionManagementResponse(Schema):
    total_deposits: int
    total_withdrawals: int
    total_transactions: int
    percent_increase_transactions: float
    percent_increase_deposits: float
    percent_increase_withdrawals: float


class BankAccountResponse(Schema):
    bank_name: str
    account_number: str


class ListTransactionWithdrawDepositResponse(Schema):
    uid: UUID
    type: str
    amount: float
    created_at: datetime
    code: str
    user: UserCreator
    bank_account: Optional[BankAccountResponse] = None
    to_user: Optional[UserCreator] = None
    group_uid: Optional[UUID] = None
