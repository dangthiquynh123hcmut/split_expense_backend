import json
from datetime import timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from django.db import transaction
from django.utils.timezone import now

from attachment.schemas.responses import AttachmentResponse
from authenticate.queries import Query as UserQuery
from event.models import Event, EventMemberBalance, EventRestructureDebt
from event.queries import Query as EventQuery
from exceptions.event import EventClosed, EventNotFound
from exceptions.expense import (
    ExpenseAlreadyVoted,
    ExpenseApprovalExpired,
    ExpenseApprovalNotFound,
    ExpenseNotFound,
    ExpenseNotPendingApproval,
    ExpenseTimeInvalid,
    ListMemberNotMatch,
)
from exceptions.users import UserNotFound
from expense.models import Expense, ExpenseApproval, ExpensePaidBy, UserSharesInExpense
from expense.queries import Query
from expense.schemas.request import ExpenseRequest, UpdateExpenseRequest
from expense.schemas.response import (
    ApprovalStatusResponse,
    ApprovalUserInfo,
    ListExpenseUser,
    UserExpense,
)
from group.models import Group, GroupMemberBalance, RestructureDebt
from group.queries import Query as GroupQuery
from message.orm.notification_queries import NotificationORM
from utils.enums import (
    ExpenseApprovalActionEnum,
    ExpenseApprovalStatusEnum,
    ExpenseStatusEnum,
    NotificationTypeEnum,
)
from utils.exceptions import GetIsDenied
from utils.functions.debt_simplification import (
    simplify_minflow,
    simplify_minflow_optimal,
)
from utils.schemas.filter_and_order_by import (
    FilterAmountSchema,
    FilterDateSchema,
    FilterEventSchema,
)
from utils.services.firebase_cm.fcm_service import FCMService
from utils.types import TUser
from wallet.orm.transaction import TransactionORM


APPROVAL_EXPIRY_HOURS = 24


class Service:
    def __init__(self):
        self.query = Query()
        self.group_query = GroupQuery()
        self.event_query = EventQuery()
        self.user_query = UserQuery()
        self.transaction_orm = TransactionORM()
        self.fcm_service = FCMService()
        self.notification_orm = NotificationORM()

    @transaction.atomic
    def create_expense(self, creator: TUser, payload: ExpenseRequest, event: Event):
        if event.status == "CLOSED":
            raise EventClosed

        if payload.expense_date is not None and (
            payload.expense_date.date() < event.event_start
            or payload.expense_date.date() > event.event_end
        ):
            raise ExpenseTimeInvalid

        if payload.end_date is not None and (
            payload.end_date.date() < event.event_start
            or payload.end_date.date() > event.event_end
        ):
            raise ExpenseTimeInvalid
        paid_by_uids = [p.user_uid for p in payload.paid_by]
        if len(paid_by_uids) != len(set(paid_by_uids)):
            raise ListMemberNotMatch
        member_uids = [m.user_uid for m in payload.list_expense_member]
        if len(member_uids) != len(set(member_uids)):
            raise ListMemberNotMatch
        paid_by_users = self.user_query.get_user_by_uids(uids=paid_by_uids)
        if len(paid_by_users) != len(payload.paid_by):
            raise UserNotFound
        list_uids = [m.user_uid for m in payload.list_expense_member]
        users = self.user_query.get_user_by_uids(uids=list_uids)
        if len(users) != len(payload.list_expense_member):
            raise UserNotFound
        event_members = self.event_query.total_event_members(event=event)
        if event_members != len(payload.list_expense_member):
            raise ListMemberNotMatch

        expense = self.query.create_expense(
            creator=creator,
            event=event,
            status=ExpenseStatusEnum.PENDING_APPROVAL,
            pending_action=ExpenseApprovalActionEnum.CREATE,
            **payload.dict(
                exclude={
                    "list_expense_member",
                    "event_uid",
                    "paid_by",
                }
            ),
        )
        paid_by_map = {p.user_uid: Decimal(str(p.amount)) for p in payload.paid_by}
        paid_by_user_map = {u.uid: u for u in paid_by_users}
        expense_paid_by_records = [
            ExpensePaidBy(
                expense=expense,
                user=paid_by_user_map[p.user_uid],
                amount=Decimal(str(p.amount)),
            )
            for p in payload.paid_by
        ]
        self.query.create_expense_paid_by(expense_paid_by=expense_paid_by_records)

        user_map = {u.uid: u for u in users}
        expense_members = [
            UserSharesInExpense(
                expense=expense,
                user=user_map.get(m.user_uid),
                amount=Decimal(str(m.amount)),
                receiver_amount=paid_by_map.get(m.user_uid, Decimal("0")),
            )
            for m in payload.list_expense_member
        ]
        self.query.create_expense_members(expense_members=expense_members)

        # Create approval records for all event members
        all_event_members = list(
            self.event_query.get_event_members(event=event).select_related("user")
        )
        self._create_approval_records(
            expense=expense,
            initiator=creator,
            event_members=all_event_members,
            action_type=ExpenseApprovalActionEnum.CREATE,
        )

        self.notification_orm.create_notification(
            from_user=creator,
            content=f"{creator.full_name} created expense '{expense.name}' in event '{expense.event.name}' — approval required.",
            type=NotificationTypeEnum.EXPENSE_APPROVAL_REQUESTED,
            related_uid=expense.uid,
            to_users=[em.user for em in all_event_members if em.user != creator],
            action_type=ExpenseApprovalActionEnum.CREATE,
        )
        self.fcm_service.send_multicast_notification(
            tokens=[
                em.user.fcm_token
                for em in all_event_members
                if em.user != creator and em.user.fcm_token
            ],
            title="Expense Approval Required",
            body=f"{creator.full_name} created expense from group '{expense.event.group.name}', event '{expense.event.name}'",
        )
        return expense

    @transaction.atomic
    def calculate_debt(self, expense: Expense, old_currency: Optional[str] = None):
        group = expense.event.group

        if group.debt_optimization == "EVENT":
            event_member_count = self.event_query.total_event_members(
                event=expense.event
            )
            if event_member_count <= 20:
                self._calculate_debt_by_event(expense=expense)
                # Also compute group-level debt by aggregating all event debts
                self._aggregate_group_debt_from_events(
                    group=group, currency=expense.currency
                )
                if old_currency and old_currency != expense.currency:
                    self.group_query.delete_restructure_debt(
                        group=group, currency=old_currency
                    )
                return

        self._calculate_debt_by_group(expense=expense, old_currency=old_currency)

    def _calculate_debt_by_group(
        self, expense: Expense, old_currency: Optional[str] = None
    ):
        balances = self.group_query.list_member_balances(
            group=expense.event.group, currency=expense.currency
        )
        balances = list(balances)
        transactions = simplify_minflow(balances)
        user_map = {
            group_member.user.uid: group_member.user
            for group_member in self.group_query.list_group_members_not_filter(
                group=expense.event.group
            )
        }
        restructure_debt = [
            RestructureDebt(
                group=expense.event.group,
                debtor=user_map.get(transactions[i][0]),
                creditor=user_map.get(transactions[i][1]),
                value=transactions[i][2],
                currency=expense.currency,
            )
            for i in range(len(transactions))
        ]
        delete_currency = old_currency if old_currency else expense.currency
        self.group_query.delete_restructure_debt(
            group=expense.event.group, currency=delete_currency
        )
        self.group_query.create_restructure_debt(restructure_debt=restructure_debt)

    def _calculate_debt_by_event(self, expense: Expense):
        """Optimal bitmask DP algorithm: compute debt at event level."""
        balances = self.event_query.list_event_member_balances(
            event=expense.event, currency=expense.currency, expense=expense
        )
        transactions = simplify_minflow_optimal(balances)
        user_map = {
            group_member.user.uid: group_member.user
            for group_member in self.group_query.list_group_members_not_filter(
                group=expense.event.group
            )
        }
        restructure_debt = [
            EventRestructureDebt(
                event=expense.event,
                debtor=user_map.get(transactions[i][0]),
                creditor=user_map.get(transactions[i][1]),
                value=transactions[i][2],
                currency=expense.currency,
            )
            for i in range(len(transactions))
        ]
        self.event_query.delete_event_restructure_debt(
            event=expense.event, currency=expense.currency
        )
        self.event_query.create_event_restructure_debt(
            restructure_debts=restructure_debt
        )

    def _aggregate_group_debt_from_events(self, group: Group, currency: str):
        """Compute group-level debt by aggregating event-level debts across all events.

        When debt_optimization == EVENT, the debt between any two people at the group
        level equals the sum of their debts across ALL events in the group.
        """
        debts = self.event_query.get_all_event_restructure_debts_by_group(
            group=group, currency=currency
        )
        user_map = {
            m.user.uid: m.user
            for m in self.group_query.list_group_members_not_filter(group=group)
        }
        restructure_debts = [
            RestructureDebt(
                group=group,
                debtor=user_map[debt["debtor"]],
                creditor=user_map[debt["creditor"]],
                value=debt["total_value"],
                currency=currency,
            )
            for debt in debts
            if debt["debtor"] in user_map and debt["creditor"] in user_map
        ]
        self.group_query.delete_restructure_debt(group=group, currency=currency)
        self.group_query.create_restructure_debt(restructure_debt=restructure_debts)

    def list_expenses_in_event(self, user: TUser, event_uid: UUID, status: str):
        event = self.event_query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        is_member_event = self.event_query.get_event_has_user(user=user, event=event)
        if not is_member_event:
            raise GetIsDenied
        return self.query.list_expenses_in_event(user=user, event=event, status=status)

    def get_expense_detail(self, user: TUser, expense_uid: UUID):
        expense = self.query.get_expense(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound
        if not UserSharesInExpense.objects.filter(expense=expense, user=user).exists():
            raise GetIsDenied
        raw_members = list(
            UserSharesInExpense.objects.filter(expense=expense)
            .select_related("user__avatar_url")
            .values_list(
                "user__uid",
                "user__full_name",
                "user__avatar_url__uid",
                "user__avatar_url__original_name",
                "user__avatar_url__public_url",
                "amount",
            )
        )
        expense_members = [
            UserExpense(
                uid=m[0],
                full_name=m[1],
                avatar_url=AttachmentResponse(
                    uid=m[2], original_name=m[3], public_url=m[4]
                )
                if m[2]
                else None,
                amount=-m[5],
            )
            for m in raw_members
        ]

        expense.list_user = expense_members

        raw_paid_by = list(
            ExpensePaidBy.objects.filter(expense=expense)
            .select_related("user__avatar_url")
            .values_list(
                "user__uid",
                "user__full_name",
                "user__avatar_url__uid",
                "user__avatar_url__original_name",
                "user__avatar_url__public_url",
                "amount",
            )
        )
        expense.paid_by = [
            UserExpense(
                uid=p[0],
                full_name=p[1],
                avatar_url=AttachmentResponse(
                    uid=p[2], original_name=p[3], public_url=p[4]
                )
                if p[2]
                else None,
                amount=p[5],
            )
            for p in raw_paid_by
        ]
        return expense

    @transaction.atomic
    def update_expense(
        self, user: TUser, expense_uid: UUID, payload: UpdateExpenseRequest
    ):
        expense = self.query.get_expense(expense_uid=expense_uid, status="ACTIVE")
        if not expense:
            raise ExpenseNotFound
        if expense.event.status == "CLOSED":
            raise EventClosed
        paid_by_uids = [p.user_uid for p in payload.paid_by]
        if len(paid_by_uids) != len(set(paid_by_uids)):
            raise ListMemberNotMatch
        member_uids = [m.user_uid for m in payload.list_expense_member]
        if len(member_uids) != len(set(member_uids)):
            raise ListMemberNotMatch
        paid_by_users = self.user_query.get_user_by_uids(uids=paid_by_uids)
        if len(paid_by_users) != len(payload.paid_by):
            raise UserNotFound
        list_uids = [m.user_uid for m in payload.list_expense_member]
        users = self.user_query.get_user_by_uids(uids=list_uids)
        if len(users) != len(payload.list_expense_member):
            raise UserNotFound
        list_user_share_in_expense = self.query.list_user_share_in_expense(
            expense=expense
        )
        if len(list_user_share_in_expense) != len(payload.list_expense_member):
            raise ListMemberNotMatch

        # Store proposed update data and set status to PENDING_UPDATE
        expense.pending_update_data = json.loads(payload.model_dump_json())
        expense.pending_action = ExpenseApprovalActionEnum.UPDATE
        expense.updated_by = user
        expense.save(
            update_fields=[
                "pending_update_data",
                "pending_action",
                "updated_by",
                "updated_at",
            ]
        )

        all_event_members = list(
            self.event_query.get_event_members(event=expense.event).select_related(
                "user"
            )
        )
        self.query.delete_expense_approvals(expense=expense)
        self._create_approval_records(
            expense=expense,
            initiator=user,
            event_members=all_event_members,
            action_type=ExpenseApprovalActionEnum.UPDATE,
        )

        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} proposed an update to expense '{expense.name}' — approval required.",
            type=NotificationTypeEnum.EXPENSE_APPROVAL_REQUESTED,
            related_uid=expense.uid,
            to_users=[em.user for em in all_event_members if em.user != user],
            action_type=ExpenseApprovalActionEnum.UPDATE,
        )
        self.fcm_service.send_multicast_notification(
            tokens=[
                em.user.fcm_token
                for em in all_event_members
                if em.user != user and em.user.fcm_token
            ],
            title="Expense Update Approval Required",
            body=f"{user.full_name} proposed an update to expense '{expense.name}'.",
        )
        return expense

    @transaction.atomic
    def soft_delete_expense(self, user: TUser, expense_uid: UUID):
        expense = self.query.get_expense(expense_uid=expense_uid, status="ACTIVE")
        if not expense:
            raise ExpenseNotFound
        if expense.event.status == "CLOSED":
            raise EventClosed

        expense.pending_action = ExpenseApprovalActionEnum.DELETE
        expense.save(update_fields=["pending_action", "updated_at"])

        all_event_members = list(
            self.event_query.get_event_members(event=expense.event).select_related(
                "user"
            )
        )
        self.query.delete_expense_approvals(expense=expense)
        self._create_approval_records(
            expense=expense,
            initiator=user,
            event_members=all_event_members,
            action_type=ExpenseApprovalActionEnum.DELETE,
        )

        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} requested deletion of expense '{expense.name}' — approval required.",
            type=NotificationTypeEnum.EXPENSE_APPROVAL_REQUESTED,
            related_uid=expense.uid,
            to_users=[em.user for em in all_event_members if em.user != user],
            action_type=ExpenseApprovalActionEnum.DELETE,
        )
        self.fcm_service.send_multicast_notification(
            tokens=[
                em.user.fcm_token
                for em in all_event_members
                if em.user != user and em.user.fcm_token
            ],
            title="Expense Deletion Approval Required",
            body=f"{user.full_name} requested deletion of expense '{expense.name}'.",
        )
        return expense

    def hard_delete_expense(self, user: TUser, expense_uid: UUID):
        expense = self.query.get_expense(expense_uid=expense_uid, status="DELETED")
        if not expense:
            raise ExpenseNotFound
        self.query.hard_delete_expense_members(expense=expense)
        self.query.hard_delete_expense(expense_uid=expense_uid)
        expense_members = self.query.list_user_share_in_expense(expense=expense)
        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} have deleted an expense {expense.name}",
            type=NotificationTypeEnum.EXPENSE_HARD_DELETED,
            related_uid=expense.uid,
            to_users=[member.user for member in expense_members],
        )
        return True

    def restore_expense(self, user: TUser, expense_uid: UUID):
        expense = self.query.get_expense(expense_uid=expense_uid, status="DELETED")
        if not expense:
            raise ExpenseNotFound
        if expense.event.status == "CLOSED":
            raise EventClosed
        self.query.restore_expense(expense_uid=expense_uid)
        self.query.restore_user_shares_in_expense(expense=expense)
        expense_members = self.query.list_user_share_in_expense(expense=expense)
        for member in expense_members:
            member.amount = member.amount - (member.receiver_amount or Decimal("0"))
        self.group_query.update_total_amount(
            group=expense.event.group,
            expense_members=expense_members,
            currency=expense.currency,
        )
        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} have restored an expense {expense.name}",
            type=NotificationTypeEnum.EXPENSE_RESTORED,
            related_uid=expense.uid,
            to_users=[member.user for member in expense_members],
        )
        return expense

    def list_expenses_by_user(
        self,
        user: TUser,
        status: str,
        filter: FilterDateSchema,
        filter_amount: FilterAmountSchema,
        filter_name: FilterEventSchema,
    ):
        query_set = self.query.list_expenses_by_user(
            user=user, status=status, filter=filter, filter_name=filter_name
        )
        expenses: list[ListExpenseUser] = [
            ListExpenseUser(
                uid=share.expense.uid,
                name=share.expense.name,
                currency=share.expense.currency,
                amount=float((share.receiver_amount or 0) - share.amount),
                created_at=share.expense.created_at,
                status=share.deleted,
                category=share.expense.category,
                event=share.expense.event.name,
            )
            for share in query_set
        ]
        if filter_amount.max_amount is not None:
            expenses = [e for e in expenses if e.amount <= filter_amount.max_amount]
        if filter_amount.min_amount is not None:
            expenses = [e for e in expenses if e.amount >= filter_amount.min_amount]
        if filter_name.event is not None:
            expenses = [e for e in expenses if e.event == filter_name.event]
        if filter_name.category is not None:
            expenses = [e for e in expenses if e.category == filter_name.category]

        return expenses

    def transaction_chart(self, user: TUser, year: int):
        return self.query.transaction_chart(user=user, year=year)

    # ── Approval helpers ──────────────────────────────────────────────────────

    def _create_approval_records(
        self,
        expense: Expense,
        initiator: TUser,
        event_members,
        action_type: str,
    ):
        expires_at = now() + timedelta(hours=APPROVAL_EXPIRY_HOURS)
        approvals = []
        for em in event_members:
            status = (
                ExpenseApprovalStatusEnum.ACCEPTED
                if em.user.uid == initiator.uid
                else ExpenseApprovalStatusEnum.PENDING
            )
            approvals.append(
                ExpenseApproval(
                    expense=expense,
                    user=em.user,
                    status=status,
                    action_type=action_type,
                    expires_at=expires_at,
                )
            )
        self.query.create_expense_approvals(approvals=approvals)

    @transaction.atomic
    def _check_and_finalize_approval(self, expense: Expense):
        """Check approval counts and finalise the pending action if threshold reached."""
        # Expire any overdue PENDING votes first
        self.query.expire_pending_approvals_for_expense(expense=expense)

        counts = self.query.count_approval_statuses(expense=expense)
        total = counts["total"]
        if total == 0:
            return

        threshold = total // 2 + 1  # strictly more than half

        if counts["accepted"] >= threshold:
            self._execute_approved_action(expense=expense)
        if counts["declined"] > threshold:
            self._execute_declined_action(expense=expense)

    @transaction.atomic
    def _execute_approved_action(self, expense: Expense):
        action = expense.pending_action
        if action == ExpenseApprovalActionEnum.CREATE:
            expense.status = ExpenseStatusEnum.ACTIVE
            expense.pending_action = ExpenseApprovalActionEnum.AVAILABLE
            expense.save(update_fields=["status", "pending_action", "updated_at"])
            # Build group balances and calculate debt (same as old create_expense)
            expense_members = list(
                self.query.list_user_share_in_expense(expense=expense)
            )
            user_exits = []
            if expense.event.group.debt_optimization == "EVENT":
                user_exits = self.event_query.get_users_in_event_member_balance(
                    event=expense.event, currency=expense.currency
                )
            if expense.event.group.debt_optimization == "GROUP":
                user_exits = self.group_query.get_users_in_group_member_balance(
                    group=expense.event.group, currency=expense.currency
                )
            if len(user_exits) < len(expense_members):
                new_user_uids = list(
                    set([m.user.uid for m in expense_members]) - set(user_exits)
                )

                if expense.event.group.debt_optimization == "EVENT":
                    new_event_member_balances = [
                        EventMemberBalance(
                            event=expense.event,
                            user=m.user,
                            currency=expense.currency,
                            balance=(m.receiver_amount or Decimal("0")) - m.amount,
                        )
                        for m in expense_members
                        if m.user.uid in new_user_uids
                    ]
                    self.event_query.create_event_member_balances(
                        event_member_balances=new_event_member_balances
                    )

                if expense.event.group.debt_optimization == "GROUP":
                    new_group_member_balances = [
                        GroupMemberBalance(
                            group=expense.event.group,
                            user=m.user,
                            currency=expense.currency,
                            balance=(m.receiver_amount or Decimal("0")) - m.amount,
                        )
                        for m in expense_members
                        if m.user.uid in new_user_uids
                    ]
                    self.group_query.create_group_member_balance(
                        group_member_balance=new_group_member_balances
                    )
            if len(user_exits) > 0:
                user_update = [m for m in expense_members if m.user.uid in user_exits]
                for m in user_update:
                    m.amount = (m.receiver_amount or Decimal("0")) - m.amount
                if expense.event.group.debt_optimization == "EVENT":
                    self.event_query.update_total_amount(
                        event=expense.event,
                        expense_members=user_update,
                        currency=expense.currency,
                    )
                if expense.event.group.debt_optimization == "GROUP":
                    self.group_query.update_total_amount(
                        group=expense.event.group,
                        expense_members=user_update,
                        currency=expense.currency,
                    )
            self.calculate_debt(expense=expense, old_currency="")
            self.notification_orm.create_notification(
                from_user=expense.creator,
                content=f"Expense '{expense.name}' has been approved and is now active.",
                type=NotificationTypeEnum.EXPENSE_APPROVED,
                related_uid=expense.uid,
                to_users=list(
                    self.event_query.get_event_members(event=expense.event).values_list(
                        "user", flat=True
                    )
                ),
            )

        elif action == ExpenseApprovalActionEnum.UPDATE:
            payload_data = expense.pending_update_data or {}
            # Rebuild UpdateExpenseRequest from stored JSON
            payload = UpdateExpenseRequest(**payload_data)
            old_currency = expense.currency

            list_user_share_in_expense = list(
                self.query.list_user_share_in_expense(expense=expense)
            )
            user_share_in_expense_map = {
                m.user.uid: m for m in list_user_share_in_expense
            }

            self.query.update_expense(
                expense=expense, payload=payload, updated_by=expense.updated_by
            )
            self.query.hard_delete_expense_members(expense=expense)
            self.query.delete_expense_paid_by(expense=expense)

            paid_by_uids = [p.user_uid for p in payload.paid_by]
            paid_by_users = self.user_query.get_user_by_uids(uids=paid_by_uids)
            list_uids = [m.user_uid for m in payload.list_expense_member]
            users = self.user_query.get_user_by_uids(uids=list_uids)

            paid_by_map = {p.user_uid: Decimal(str(p.amount)) for p in payload.paid_by}
            paid_by_user_map = {u.uid: u for u in paid_by_users}
            expense_paid_by_records = [
                ExpensePaidBy(
                    expense=expense,
                    user=paid_by_user_map[p.user_uid],
                    amount=Decimal(str(p.amount)),
                )
                for p in payload.paid_by
            ]
            self.query.create_expense_paid_by(expense_paid_by=expense_paid_by_records)

            user_map = {u.uid: u for u in users}
            expense_members = [
                UserSharesInExpense(
                    expense=expense,
                    user=user_map.get(m.user_uid),
                    amount=Decimal(str(m.amount)),
                    receiver_amount=paid_by_map.get(m.user_uid, Decimal("0")),
                )
                for m in payload.list_expense_member
            ]
            self.query.create_expense_members(expense_members=expense_members)

            if old_currency != payload.currency:
                self.group_query.update_currency_in_group_member_balance(
                    group=expense.event.group,
                    old_currency=old_currency,
                    new_currency=payload.currency,
                )
            if expense.event.group.debt_optimization == "EVENT":
                user_exits = self.event_query.get_users_in_event_member_balance(
                    event=expense.event, currency=payload.currency
                )
            if expense.event.group.debt_optimization == "GROUP":
                user_exits = self.group_query.get_users_in_group_member_balance(
                    group=expense.event.group, currency=payload.currency
                )
            if len(user_exits) < len(expense_members):
                new_user_uids = list(
                    set([m.user.uid for m in expense_members]) - set(user_exits)
                )
                if expense.event.group.debt_optimization == "EVENT":
                    new_event_member_balances = [
                        EventMemberBalance(
                            event=expense.event,
                            user=m.user,
                            currency=payload.currency,
                            balance=(m.receiver_amount or Decimal("0")) - m.amount,
                        )
                        for m in expense_members
                        if m.user.uid in new_user_uids
                    ]
                    self.event_query.create_event_member_balances(
                        event_member_balances=new_event_member_balances
                    )
                if expense.event.group.debt_optimization == "GROUP":
                    new_group_member_balances = [
                        GroupMemberBalance(
                            group=expense.event.group,
                            user=m.user,
                            currency=payload.currency,
                            balance=(m.receiver_amount or Decimal("0")) - m.amount,
                        )
                        for m in expense_members
                        if m.user.uid in new_user_uids
                    ]
                    self.group_query.create_group_member_balance(
                        group_member_balance=new_group_member_balances
                    )
            if len(user_exits) > 0:
                user_update = [m for m in expense_members if m.user.uid in user_exits]
                for member in user_update:
                    old = user_share_in_expense_map.get(member.user.uid)
                    new_net = (member.receiver_amount or Decimal("0")) - member.amount
                    member.amount = (
                        (new_net - ((old.receiver_amount or Decimal("0")) - old.amount))
                        if old
                        else new_net
                    )
                if expense.event.group.debt_optimization == "EVENT":
                    self.event_query.update_total_amount(
                        event=expense.event,
                        expense_members=user_update,
                        currency=payload.currency,
                    )
                if expense.event.group.debt_optimization == "GROUP":
                    self.group_query.update_total_amount(
                        group=expense.event.group,
                        expense_members=user_update,
                        currency=payload.currency,
                    )

            expense.pending_action = ExpenseApprovalActionEnum.AVAILABLE
            expense.pending_update_data = None
            expense.save(
                update_fields=["pending_action", "pending_update_data", "updated_at"]
            )
            self.calculate_debt(expense=expense, old_currency=old_currency)

        elif action == ExpenseApprovalActionEnum.DELETE:
            expense_members = list(
                self.query.list_user_share_in_expense(expense=expense)
            )
            for member in expense_members:
                member.amount = (member.receiver_amount or Decimal("0")) - member.amount
            if expense.event.group.debt_optimization == "EVENT":
                self.event_query.update_total_amount(
                    event=expense.event,
                    expense_members=expense_members,
                    currency=expense.currency,
                )
            if expense.event.group.debt_optimization == "GROUP":
                self.group_query.update_total_amount(
                    group=expense.event.group,
                    expense_members=expense_members,
                    currency=expense.currency,
                )
            self.query.soft_delete_expense_members(expense=expense)
            self.query.soft_delete_expense(expense_uid=expense.uid)
            expense.pending_action = ExpenseApprovalActionEnum.AVAILABLE
            expense.save(update_fields=["pending_action", "updated_at"])
            self.calculate_debt(expense=expense, old_currency="")

    @transaction.atomic
    def _execute_declined_action(self, expense: Expense):
        action = expense.pending_action
        if not action:
            return
        if action == ExpenseApprovalActionEnum.CREATE:
            expense.status = ExpenseStatusEnum.DECLINED
            expense.pending_action = ExpenseApprovalActionEnum.AVAILABLE
            expense.save(update_fields=["status", "pending_action", "updated_at"])
        elif action == ExpenseApprovalActionEnum.UPDATE:
            expense.pending_action = ExpenseApprovalActionEnum.AVAILABLE
            expense.pending_update_data = None
            expense.save(
                update_fields=["pending_action", "pending_update_data", "updated_at"]
            )
        elif action == ExpenseApprovalActionEnum.DELETE:
            expense.pending_action = ExpenseApprovalActionEnum.AVAILABLE
            expense.save(update_fields=["pending_action", "updated_at"])

        all_members = list(
            self.event_query.get_event_members(event=expense.event).select_related(
                "user"
            )
        )
        self.notification_orm.create_notification(
            from_user=expense.creator,
            content=f"The {action.lower()} request for expense '{expense.name}' has been declined.",
            type=NotificationTypeEnum.EXPENSE_APPROVAL_DECLINED,
            related_uid=expense.uid,
            to_users=[em.user for em in all_members],
        )

    # ── Public approval API methods ───────────────────────────────────────────

    def get_approval_status(
        self,
        expense_uid: UUID,
        action_type: str,
    ) -> ApprovalStatusResponse:
        expense = self.query.get_expense(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound

        # Lazily expire overdue votes
        self.query.expire_pending_approvals_for_expense(expense=expense)

        # Get approvals: filter by action_type if provided, else get all
        approvals = list(
            self.query.get_expense_approvals_by_action_type(
                expense=expense, action_type=action_type
            )
        )
        if not approvals:
            raise ExpenseNotPendingApproval
        counts = self.query.count_approval_statuses_by_action_type(
            expense=expense, action_type=action_type
        )

        total = counts["total"]
        threshold = total // 2 + 1

        # Determine final status
        if counts["accepted"] >= threshold:
            final_status = "APPROVED"
        elif counts["declined"] >= threshold or counts["pending"] == 0:
            final_status = "DECLINED"
        else:
            final_status = "PENDING"

        accepted_users, declined_users, pending_users = [], [], []
        expires_at = None
        for a in approvals:
            info = ApprovalUserInfo(
                uid=a.user.uid,
                full_name=a.user.full_name,
                avatar_url=a.user.avatar_url
                if hasattr(a.user, "avatar_url") and a.user.avatar_url
                else None,
                voted_at=a.updated_at
                if a.status != ExpenseApprovalStatusEnum.PENDING
                else None,
            )
            if a.status == ExpenseApprovalStatusEnum.ACCEPTED:
                accepted_users.append(info)
            elif a.status == ExpenseApprovalStatusEnum.DECLINED:
                declined_users.append(info)
            else:
                pending_users.append(info)
            if expires_at is None:
                expires_at = a.expires_at

        return ApprovalStatusResponse(
            total_members=total,
            accepted_count=counts["accepted"],
            declined_count=counts["declined"],
            pending_count=counts["pending"],
            threshold=threshold,
            expires_at=expires_at,
            action_type=action_type,
            final_status=final_status,
            accepted_users=accepted_users,
            declined_users=declined_users,
            pending_users=pending_users,
        )

    @transaction.atomic
    def vote_on_expense(self, user: TUser, expense_uid: UUID, action: str) -> bool:
        expense = self.query.get_expense(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound
        approval = self.query.get_expense_approval(expense=expense, user=user)
        if not approval:
            raise ExpenseApprovalNotFound
        if approval.status != ExpenseApprovalStatusEnum.PENDING:
            raise ExpenseAlreadyVoted
        if approval.expires_at < now():
            raise ExpenseApprovalExpired

        self.query.update_approval_status(approval=approval, status=action)
        self._check_and_finalize_approval(expense=expense)
        return True
