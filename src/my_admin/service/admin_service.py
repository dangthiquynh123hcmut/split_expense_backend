from typing import Optional
from uuid import UUID

from django.db import transaction

from attachment.schemas.responses import AttachmentResponse
from authenticate.queries import Query as Auth_Query
from event.queries import Query as EventQuery
from exceptions.users import UserNotFound
from expense.models import Expense
from expense.queries import Query as ExpenseQuery
from group.queries import Query as GroupQuery
from group.schemas.response import GroupName
from message.orm.message_queries import MessageORM
from message.orm.notification_queries import NotificationORM
from message.schemas.request import MessageFilter
from my_admin.schemas.request import FilterTransactionSchema, OrderByBalanceSchema
from my_admin.schemas.response import (
    AdminGroupResponse,
    ExpenseCategoryResponse,
    GroupStatisticsResponse,
    NotificationManagementResponse,
    ParticipatingGroupsResponse,
    RatingResponse,
    TodayOverviewResponse,
    UserInsightsResponse,
)
from user.queries import Query as UserQuery
from utils.schemas.filter_and_order_by import (
    FilterDateSchema,
    FilterEventAdminSchema,
    FilterExpenseAdminSchema,
    FilterFullNameSchema,
    FilterNameSchema,
)
from utils.services.firebase_cm.fcm_service import FCMService
from utils.types import TUser
from wallet.orm.deposit import DepositORM
from wallet.orm.transaction import TransactionORM
from wallet.orm.withdraw import WithdrawORM

from ..orm.admin_orm import Query
from ..schemas.request import (
    CreateNotificationResquest,
    FilterNotificationSchema,
    UserFilter,
)
from ..schemas.response import (
    BankAccountResponse,
    EventManagementResponse,
    ExpenseAttachmentResponse,
    ExpenseInEventResponse,
    ExpenseItemResponse,
    ExpenseManagementResponse,
    ListEventMemberResponse,
    ListEventResponse,
    ListExpenseResponse,
    ListTransactionWithdrawDepositResponse,
    MessageGroupResponse,
    MessageInGroupResponse,
    MessageItemResponse,
    MessageManagementResponse,
    NameEvent,
    SplitExpenseResponse,
    TransactionManagementResponse,
    UserCreator,
    UserEventSchema,
    UserInforResponse,
    UserSharesInExpenseResponse,
)


class AdminService:
    def __init__(self):
        self.query = Query()
        self.auth_query = Auth_Query()
        self.withdraw_query = WithdrawORM()
        self.deposit_query = DepositORM()
        self.transaction_query = TransactionORM()
        self.expense_query = ExpenseQuery()
        self.group_query = GroupQuery()
        self.events_query = EventQuery()
        self.message_query = MessageORM()
        self.notification_query = NotificationORM()
        self.user_query = UserQuery()
        self.fcm_service = FCMService()

    def list_users(
        self,
        filter: Optional[UserFilter] = None,
        order_by: Optional[OrderByBalanceSchema] = None,
    ):
        return self.query.list_users(filter=filter, order_by=order_by)

    def today_overview(self):
        total_users_today, total_users_yesterday = self.auth_query.total_users_use_app()
        total_tranfer_today, total_tranfer_yesterday = (
            self.transaction_query.total_transactions_today()
        )
        total_deposit_today, total_deposit_yesterday = (
            self.deposit_query.total_deposit_today()
        )
        total_withdraw_today, total_withdraw_yesterday = (
            self.withdraw_query.total_withdraw_today()
        )
        total_transactions_today = (
            total_deposit_today + total_withdraw_today + total_tranfer_today
        )
        total_transactions_yesterday = (
            total_deposit_yesterday + total_withdraw_yesterday + total_tranfer_yesterday
        )
        total_withdraw_money_today, total_withdraw_money_yesterday = (
            self.withdraw_query.total_withdraw_money_today()
        )
        total_deposit_today, total_deposit_yesterday = (
            self.deposit_query.total_deposit_money_today()
        )
        total_money_today = total_deposit_today + total_withdraw_money_today
        total_money_yesterday = total_deposit_yesterday + total_withdraw_money_yesterday
        new_users_today, new_users_yesterday = self.auth_query.count_new_users()

        return TodayOverviewResponse(
            total_users=total_users_today,
            total_transactions=total_transactions_today,
            total_money=total_money_today,
            new_users=new_users_today,
            percent_increase_users=(
                (total_users_today - total_users_yesterday)
                / total_users_yesterday
                * 100
                if total_users_yesterday > 0
                else 100.0
            ),
            percent_increase_transactions=(
                (total_transactions_today - total_transactions_yesterday)
                / total_transactions_yesterday
                * 100
                if total_transactions_yesterday > 0
                else 100.0
            ),
            percent_increase_money=(
                (total_money_today - total_money_yesterday)
                / total_money_yesterday
                * 100
                if total_money_yesterday > 0
                else 100.0
            ),
            percent_increase_new_users=(
                (new_users_today - new_users_yesterday) / new_users_yesterday * 100
                if new_users_yesterday > 0
                else 100.0
            ),
        )

    def user_insights(self, year: int) -> list[UserInsightsResponse]:
        insights_data = self.query.user_insights(year)

        return [
            UserInsightsResponse(
                month_year=insight["month_year"],
                new_users=insight["new_users"],
                loyal_users=insight["loyal_users"],
                return_users=insight["return_users"],
            )
            for insight in insights_data
        ]

    def expense_categories(self) -> list[ExpenseCategoryResponse]:
        categories_data = self.expense_query.expense_categories()

        return [
            ExpenseCategoryResponse(
                category=category["category"],
                total_amount=category["total_amount"],
            )
            for category in categories_data
        ]

    def rating(self, filter: FilterDateSchema) -> list[RatingResponse]:
        rating_data = self.query.rating(filter=filter)

        return [
            RatingResponse(
                date=rating["date"],
                rate=rating["avg_rate"],
            )
            for rating in rating_data
        ]

    def group_statistics(self) -> GroupStatisticsResponse:
        total_groups, total_groups_last_month = self.group_query.count_groups()
        total_members, total_members_last_month = self.group_query.count_members()
        active_groups, active_groups_last_month = self.group_query.count_active_groups()
        return GroupStatisticsResponse(
            total_groups=total_groups,
            total_members=total_members,
            active_groups=active_groups,
            percent_increase_groups=(
                (total_groups - total_groups_last_month) / total_groups_last_month * 100
                if total_groups_last_month > 0
                else 100.0
            ),
            percent_increase_members=(
                (total_members - total_members_last_month)
                / total_members_last_month
                * 100
                if total_members_last_month > 0
                else 100.0
            ),
            percent_increase_active_groups=(
                (active_groups - active_groups_last_month)
                / active_groups_last_month
                * 100
                if active_groups_last_month > 0
                else 100.0
            ),
        )

    @transaction.atomic
    def deactivate_group(self, group_uid: UUID) -> bool:
        self.group_query.deactivate_groups(group_uid=group_uid)
        self.group_query.deactivate_group_members_in_group(group_uid=group_uid)
        return True

    def active_groups(self, group_uid: UUID) -> bool:
        self.group_query.active_groups(group_uid=group_uid)
        self.group_query.active_group_members_in_group(group_uid=group_uid)
        return True

    def list_groups(self, filter: FilterNameSchema) -> list[AdminGroupResponse]:
        return self.group_query.list_groups_admin(filter=filter)

    def event_management(self) -> EventManagementResponse:
        total_events, total_events_last_month = self.events_query.count_events()
        total_members, total_members_last_month = (
            self.events_query.count_event_members()
        )
        active_events, active_events_last_month = (
            self.events_query.count_active_events()
        )
        total_finished_events, total_finished_events_last_month = (
            self.events_query.count_finished_events()
        )
        return EventManagementResponse(
            total_events=total_events,
            total_members=total_members,
            active_events=active_events,
            total_finished_events=total_finished_events,
            percent_increase_events=(
                (total_events - total_events_last_month) / total_events_last_month * 100
                if total_events_last_month > 0
                else 100.0
            ),
            percent_increase_members=(
                (total_members - total_members_last_month)
                / total_members_last_month
                * 100
                if total_members_last_month > 0
                else 100.0
            ),
            percent_increase_active_events=(
                (active_events - active_events_last_month)
                / active_events_last_month
                * 100
                if active_events_last_month > 0
                else 100.0
            ),
            percent_increase_finished_events=(
                (total_finished_events - total_finished_events_last_month)
                / total_finished_events_last_month
                * 100
                if total_finished_events_last_month > 0
                else 100.0
            ),
        )

    def list_events(self, filter: FilterEventAdminSchema) -> list[ListEventResponse]:
        query = self.events_query.list_events_admin(filter=filter)
        return [
            ListEventResponse(
                event_uid=query.uid,
                event_name=query.name,
                event_description=query.description,
                event_start=query.event_start,
                event_end=query.event_end,
                status=query.status,
                creator=UserCreator.from_orm(query.creator),
                group=GroupName.from_orm(query.group),
            )
            for query in query
        ]

    def list_event_members(
        self, event_uid: UUID, filter: FilterFullNameSchema
    ) -> list[ListEventMemberResponse]:
        query = self.events_query.list_event_members_admin(
            event_uid=event_uid, filter=filter
        )
        return [
            ListEventMemberResponse(
                event_member_uid=member.event_member_uid,
                user_infor=UserEventSchema.from_orm(member.user),
                status=member.status,
            )
            for member in query
        ]

    def get_expenses_in_event(self, event_uid: UUID) -> ExpenseInEventResponse:
        expenses_data = self.expense_query.get_expenses_in_event(event_uid=event_uid)
        total_amount = sum(expense.total_amount for expense in expenses_data)
        expenses_list = [
            ExpenseItemResponse(
                name=expense.name,
                status=expense.status,
                category=expense.category,
                total_amount=expense.total_amount,
                currency=expense.currency,
                expense_date=expense.expense_date,
                paid_by=UserEventSchema.from_orm(expense.paid_by),
                creator=UserEventSchema.from_orm(expense.creator),
                event=NameEvent(uid=expense.event.uid, name=expense.event.name),
                split_type=expense.split_type,
                uid=expense.uid,
                note=expense.note,
            )
            for expense in expenses_data
        ]
        return ExpenseInEventResponse(
            total_amount=total_amount,
            expenses=expenses_list,
        )

    def deactivate_event(self, event_uid: UUID) -> bool:
        self.events_query.deactivate_event(event_uid=event_uid)
        return True

    def active_event(self, event_uid: UUID) -> bool:
        self.events_query.active_event(event_uid=event_uid)
        return True

    def expense_management(self) -> ExpenseManagementResponse:
        total_expenses, total_expenses_last_month = self.expense_query.count_expenses()
        active_expenses, active_expenses_last_month = (
            self.expense_query.count_active_expenses()
        )
        total_expired_expenses, total_expired_expenses_last_month = (
            self.expense_query.count_expired_expenses()
        )
        total_expense_amount, total_expense_amount_last_month = (
            self.expense_query.count_expense_amount()
        )
        total_expense_members, total_expense_members_last_month = (
            self.expense_query.count_expense_members()
        )

        return ExpenseManagementResponse(
            total_expenses=total_expenses,
            total_avg_amount=(total_expense_amount / total_expense_members)
            if total_expense_members > 0
            else 0,
            active_expenses=active_expenses,
            total_expired_expenses=total_expired_expenses,
            percent_increase_expenses=(
                (total_expenses - total_expenses_last_month)
                / total_expenses_last_month
                * 100
                if total_expenses_last_month > 0
                else 100.0
            ),
            percent_increase_active_expenses=(
                (active_expenses - active_expenses_last_month)
                / active_expenses_last_month
                * 100
                if active_expenses_last_month > 0
                else 100.0
            ),
            percent_increase_avg_amount=(
                (total_expense_amount - total_expense_amount_last_month)
                / (total_expense_members - total_expense_members_last_month)
                * 100
                if (total_expense_members - total_expense_members_last_month) > 0
                else 100.0
            ),
            percent_increase_expired_expenses=(
                (total_expired_expenses - total_expired_expenses_last_month)
                / total_expired_expenses_last_month
                * 100
                if total_expired_expenses_last_month > 0
                else 100.0
            ),
        )

    def get_all_expenses(self, filter: FilterExpenseAdminSchema) -> ExpenseItemResponse:
        expenses_data = self.expense_query.get_all_expenses(filter=filter)
        return [
            ExpenseItemResponse(  # type: ignore
                status=expense.status,
                category=expense.category,
                total_amount=expense.total_amount,
                currency=expense.currency,
                expense_date=expense.expense_date,
                paid_by=UserEventSchema.from_orm(expense.paid_by),
                creator=UserEventSchema.from_orm(expense.creator),
                name=expense.name,
                event=NameEvent(uid=expense.event.uid, name=expense.event.name),
                split_type=expense.split_type,
                uid=expense.uid,
                note=expense.note,
            )
            for expense in expenses_data
        ]

    def deactivate_expense(self, expense_uid: UUID) -> bool:
        self.expense_query.deactivate_expense(expense_uid=expense_uid)
        return True

    def active_expense(self, expense_uid: UUID) -> bool:
        self.expense_query.active_expense(expense_uid=expense_uid)
        return True

    def get_split_expense(self, expense_uid: UUID) -> SplitExpenseResponse:
        expense_data = self.expense_query.get_expense_by_uid(expense_uid=expense_uid)
        user_shares_data = self.expense_query.get_user_shares_in_expense(
            expense=expense_data
        )
        list_user_shares = [
            UserSharesInExpenseResponse(
                user=UserEventSchema.from_orm(user_share.user),
                amount=user_share.amount,
            )
            for user_share in user_shares_data
        ]
        return SplitExpenseResponse(
            total_amount=expense_data.total_amount,
            currency=expense_data.currency,
            split_type=expense_data.split_type,
            list_user_shares=list_user_shares,
        )

    def get_expense_attachments(self, expense: Expense) -> ExpenseAttachmentResponse:
        return self.expense_query.get_expense_attachments(expense=expense)

    def message_management(self) -> MessageManagementResponse:
        total_message, total_message_last_month = (
            self.message_query.message_management()
        )
        total_group, total_group_last_month = self.group_query.count_active_groups()
        message_today, message_yesterday = self.message_query.total_messages_today()
        total_attachments, total_attachments_last_month = (
            self.message_query.total_attachments()
        )
        return MessageManagementResponse(
            total_messages=total_message,
            active_groups=total_group,
            message_today=message_today,
            attachments=total_attachments,
            percent_increase_messages=(
                (total_message - total_message_last_month)
                / total_message_last_month
                * 100
                if total_message_last_month > 0
                else 100.0
            ),
            percent_increase_active_groups=(
                (total_group - total_group_last_month) / total_group_last_month * 100
                if total_group_last_month > 0
                else 100.0
            ),
            percent_increase_attachments=(
                (total_attachments - total_attachments_last_month)
                / total_attachments_last_month
                * 100
                if total_attachments_last_month > 0
                else 100.0
            ),
            percent_increase_message_today=(
                (message_today - message_yesterday) / message_yesterday * 100
                if message_yesterday > 0
                else 100.0
            ),
        )

    def list_messages_group(self) -> MessageGroupResponse:
        groups = self.message_query.list_messages_group()

        return [
            MessageGroupResponse(  # type: ignore
                uid=group.uid,
                group_name=group.name,
                total_members=group.total_members,
                total_messages=group.total_messages,
                total_messages_unread=group.total_messages_unread,
                last_message=group.last_message.isoformat()
                if group.last_message
                else None,
                last_message_content=group.last_message_content
                if group.last_message_content
                else None,
            )
            for group in groups
        ]

    def get_messages_in_group(
        self, group_uid: UUID, filter: MessageFilter
    ) -> MessageInGroupResponse:
        group = self.group_query.get_group_by_uid(group_uid=group_uid)
        messages = self.message_query.get_messages_in_group(
            group_uid=group_uid, filter=filter
        )
        total_messages = len(messages)
        return [
            MessageInGroupResponse(  # type: ignore
                total_messages=total_messages,
                name=group.name,
                total_members=group.group_member_fk_group.count(),
                messages=[
                    MessageItemResponse(
                        uid=msg.uid,
                        sender=UserCreator.from_orm(msg.user),
                        content=msg.content,
                        created_at=msg.created_at,
                        status=msg.status,
                        attachments=[
                            AttachmentResponse.from_orm(attachment.attachment)
                            for attachment in msg.message_attachment_fk_message.all()
                        ]
                        if msg.message_attachment_fk_message.exists()
                        else None,
                    )
                    for msg in messages
                ],
                avatar_url=AttachmentResponse.from_orm(group.avatar_url)
                if group.avatar_url
                else None,
            )
        ]

    def get_info_user(self, user_uid: UUID) -> UserInforResponse:
        user = self.auth_query.get_info_user(user_uid=user_uid)
        return UserInforResponse(
            uid=user.uid,
            email=user.email,
            full_name=user.full_name,
            phone_number=user.phone_number,
            avatar_url=AttachmentResponse.from_orm(user.avatar_url)
            if user.avatar_url
            else None,
            status=user.is_active,
            joined=user.date_joined,
            role=user.role,
            last_login=user.last_login,
            total_expenses=self.expense_query.total_expenses_by_user(user_uid=user_uid),
            total_groups=self.group_query.total_groups_by_user(user_uid=user_uid),
            total_balance=self.group_query.total_balances_by_user(user_uid=user_uid),
        )

    def activate_user(self, user_uid: UUID) -> bool:
        user = self.auth_query.get_info_user(user_uid=user_uid)
        if not user:
            raise UserNotFound
        self.auth_query.activate_user(user=user)
        return True

    def list_participating_groups(
        self,
        user_uid: UUID,
        filter: FilterNameSchema,
    ) -> list[ParticipatingGroupsResponse]:
        groups = self.group_query.list_participating_groups(
            user_uid=user_uid,
            filter=filter,
        )
        return [
            ParticipatingGroupsResponse(
                group_uid=group.uid,
                group_name=group.name,
                role="Leader" if group.leader.uid == user_uid else "Member",
                joined_at=group.joined_at,
            )
            for group in groups
        ]

    def list_user_expenses(
        self,
        user_uid: UUID,
        filter: FilterNameSchema,
    ) -> list[ListExpenseResponse]:
        expenses = self.expense_query.list_user_expenses(
            user_uid=user_uid,
            filter=filter,
        )
        return [
            ListExpenseResponse(
                expense_uid=expense.uid,
                name=expense.name,
                amount=expense.amount,
                currency=expense.currency,
                expense_date=expense.expense_date,
                end_date=expense.end_date,
            )
            for expense in expenses
        ]

    def transactions_management(self):
        total_deposits, total_deposits_last_month = self.deposit_query.count_deposits()
        total_withdrawals, total_withdrawals_last_month = (
            self.withdraw_query.count_withdrawals()
        )
        total_transactions, total_transactions_last_month = (
            self.transaction_query.count_transactions()
        )
        return TransactionManagementResponse(
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            total_transactions=total_transactions,
            percent_increase_transactions=(
                (total_transactions - total_transactions_last_month)
                / total_transactions_last_month
                * 100
                if total_transactions_last_month > 0
                else 100.0
            ),
            percent_increase_deposits=(
                (total_deposits - total_deposits_last_month)
                / total_deposits_last_month
                * 100
                if total_deposits_last_month > 0
                else 100.0
            ),
            percent_increase_withdrawals=(
                (total_withdrawals - total_withdrawals_last_month)
                / total_withdrawals_last_month
                * 100
                if total_withdrawals_last_month > 0
                else 100.0
            ),
        )

    def list_transactions_withdraws_and_deposits(
        self, filter: FilterTransactionSchema
    ) -> ListTransactionWithdrawDepositResponse:
        total_list = []
        if filter.type is None:
            transactions = (
                self.transaction_query.list_transactions_withdraws_and_deposits(
                    userName=filter.search
                )
            )
            withdraws = self.withdraw_query.list_withdraws(userName=filter.search)
            deposits = self.deposit_query.list_deposits(userName=filter.search)
            total_list = list(transactions) + list(withdraws) + list(deposits)
            total_list.sort(key=lambda x: x.created_at, reverse=True)
        elif filter.type == "withdraw":
            total_list = list(
                self.withdraw_query.list_withdraws(userName=filter.search)
            )
        elif filter.type == "deposit":
            total_list = list(self.deposit_query.list_deposits(userName=filter.search))
        elif filter.type == "in_app":
            total_list = list(
                self.transaction_query.list_transactions_withdraws_and_deposits(
                    userName=filter.search
                )
            )

        results = []
        for trans in total_list:
            if hasattr(trans, "from_user"):
                user = UserCreator.from_orm(trans.from_user)
            else:
                user = UserCreator.from_orm(trans.user)

            results.append(
                ListTransactionWithdrawDepositResponse(
                    uid=trans.uid,
                    type=trans.type,
                    amount=trans.amount,
                    currency=trans.currency if hasattr(trans, "currency") else "VND",
                    created_at=trans.created_at,
                    code=trans.code,
                    user=user,
                    bank_account=BankAccountResponse.from_orm(trans.bank_account)
                    if hasattr(trans, "bank_account") and trans.bank_account
                    else None,
                    to_user=UserCreator.from_orm(trans.to_user)
                    if hasattr(trans, "to_user")
                    else None,
                    group_uid=trans.group.uid
                    if hasattr(trans, "group") and trans.group
                    else None,
                )
            )
        return results  # type: ignore

    def get_notification_management(self):
        total_notifications, total_notifications_last_month = (
            self.notification_query.total_notifications()
        )
        total_users, total_users_last_month = self.user_query.total_users_in_app()
        notifications_today, notifications_yesterday = (
            self.notification_query.total_notifications_today()
        )
        return NotificationManagementResponse(
            total_notifications=total_notifications,
            total_users=total_users,
            notifications_today=notifications_today,
            percent_increase_users=(
                (total_users - total_users_last_month) / total_users_last_month * 100
                if total_users_last_month > 0
                else 100.0
            ),
            percent_increase_total_notifications=(
                (total_notifications - total_notifications_last_month)
                / total_notifications_last_month
                * 100
                if total_notifications_last_month > 0
                else 100.0
            ),
            percent_increase_notifications_today=(
                (notifications_today - notifications_yesterday)
                / notifications_yesterday
                * 100
                if notifications_yesterday > 0
                else 100.0
            ),
        )

    def list_notifications_admin(
        self, filter: FilterNotificationSchema
    ) -> list[NotificationManagementResponse]:
        return self.notification_query.list_notifications_admin(filter=filter)

    def create_notification(
        self,
        from_user: TUser,
        body: CreateNotificationResquest,
    ):
        if body.type == "Broadcast":
            members = self.auth_query.get_all_active_users()
        else:
            members = self.auth_query.get_user_by_uids(uids=body.to_user_uids)
            if len(members) != len(body.to_user_uids):  # type: ignore
                raise UserNotFound
        self.fcm_service.send_multicast_notification(
            tokens=[member.fcm_token for member in members if member.fcm_token],
            title=body.type,
            body=body.content,
        )
        return self.notification_query.create_notification(
            from_user=from_user,
            related_uid=body.related_uid,
            content=body.content,
            type=body.type,
            to_users=members,
        )

    def delete_notification(self, notification_uid: UUID):
        self.notification_query.delete_notification(notification_uid=notification_uid)

    def list_user_login_history(self, user_uid: UUID):
        return self.query.list_user_login_history(user_uid=user_uid)
