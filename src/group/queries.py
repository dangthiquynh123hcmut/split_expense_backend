from collections import defaultdict
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from channels.db import database_sync_to_async
from django.db.models import (
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    Prefetch,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Abs, Coalesce, Round

from attachment.models import Attachment
from authenticate.models import User
from event.models import Event
from expense.models import Expense, UserSharesInExpense
from expense.schemas.response import ExpenseEvent, NameExpense
from utils.schemas.filter_and_order_by import (
    FilterFullNameSchema,
    FilterMonthSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
    OrderByNameAndUpdatedAtSchema,
)
from utils.types import TUser

from .models import Group, GroupMember, GroupMemberBalance, RestructureDebt


class Query:
    @staticmethod
    def create_group(leader: User, name: str):
        return Group.objects.create(leader=leader, name=name)

    @staticmethod
    def create_group_members(group_members: List[GroupMember]):
        GroupMember.objects.bulk_create(group_members)
        return

    @staticmethod
    def list_groups(
        user: TUser, filter: FilterNameSchema, order_by: OrderByNameAndUpdatedAtSchema
    ):
        queryset = Group.objects.filter(
            group_member_fk_group__user__uid=user.uid, status="ACTIVE"
        ).distinct()
        if filter:
            queryset = queryset.filter(filter.get_filter_expression())

        if order_by:
            queryset = queryset.order_by(order_by.get_order_by_expression())

        return queryset

    @staticmethod
    @database_sync_to_async
    def get_group(group_uid: UUID):
        return Group.objects.filter(uid=group_uid, status="ACTIVE").first()

    @staticmethod
    def get_group_sync(group_uid: UUID):
        try:
            return Group.objects.get(uid=group_uid, status="ACTIVE")
        except Group.DoesNotExist:
            return None

    @staticmethod
    def get_group_has_user(user: TUser, group: Group):
        try:
            return GroupMember.objects.get(user=user, group=group)
        except GroupMember.DoesNotExist:
            return None

    @staticmethod
    def update_group(group: Group, name: str):
        if group:
            group.name = name
            group.save()
        return group

    @staticmethod
    def leave_group(user: TUser, group: Group):
        return GroupMember.objects.filter(user=user, group=group).delete()

    @staticmethod
    def delete_group(group: Group):
        return Group.objects.filter(uid=group.uid).delete()

    @staticmethod
    def get_members_by_uids(group: Group, uids: List[UUID]):
        return GroupMember.objects.filter(
            user_id__in=uids, status="ACTIVE", group=group
        )

    @staticmethod
    def list_uids_members(group: Group):
        return GroupMember.objects.filter(group=group, status="ACTIVE").values_list(
            "user__uid", flat=True
        )

    @staticmethod
    def list_group_members(
        group: Group,
        filter: FilterFullNameSchema,
        order_by: OrderByFullNameAndUpdatedAtSchema,
    ):
        query = GroupMember.objects.filter(group=group, status="ACTIVE")
        if filter and filter.search:
            query = query.filter(filter.filter_search(filter.search))

        if order_by:
            query = query.annotate(full_name=F("user__full_name")).order_by(
                order_by.get_order_by_expression()
            )
        return query

    @staticmethod
    def list_group_members_not_filter(group: Group):
        return GroupMember.objects.filter(group=group, status="ACTIVE")

    @staticmethod
    def get_group_detail(group_uid: UUID):
        return Group.objects.filter(uid=group_uid, status="ACTIVE").first()

    @staticmethod
    def list_events_in_a_group(
        group: Group,
        filter: FilterNameSchema,
        order_by: OrderByNameAndUpdatedAtSchema,
    ):
        queryset = Event.objects.filter(group=group, status="ACTIVE").distinct()
        if filter:
            queryset = queryset.filter(filter.get_filter_expression())

        if order_by:
            queryset = queryset.order_by(order_by.get_order_by_expression())

        return queryset

    @staticmethod
    def add_attachment(group: Group, attachment: Attachment):
        group.avatar_url = attachment
        group.save()
        return group

    @staticmethod
    def get_expenses_in_group(group: Group):
        return Expense.objects.filter(event__group=group, status="ACTIVE").distinct()

    @staticmethod
    def get_users_in_group_member_balance(group: Group, currency: str):
        return GroupMemberBalance.objects.filter(
            group=group, currency=currency
        ).values_list("user__uid", flat=True)

    @staticmethod
    def create_group_member_balance(group_member_balance: List[GroupMemberBalance]):
        return GroupMemberBalance.objects.bulk_create(group_member_balance)

    @staticmethod
    def update_total_amount(group: Group, expense_members: List[UserSharesInExpense]):
        whens = []
        users = []

        for em in expense_members:
            users.append(em.user)
            whens.append(When(user=em.user, then=F("balance") + em.amount))

        return GroupMemberBalance.objects.filter(group=group, user__in=users).update(
            balance=Case(*whens, default=F("balance"))
        )

    @staticmethod
    def list_expenses_in_a_group(
        user: User,
        group: Group,
        status: str,
        filter: FilterMonthSchema,
    ):
        expense_members = (
            UserSharesInExpense.objects.filter(
                expense__event__group=group, expense__status=status, user=user
            )
            .select_related("expense", "expense__event")
            .order_by("expense__event__name", "expense__created_at")
        )
        if filter:
            expense_members = expense_members.filter(filter.get_filter_expression())

        grouped: dict[str, list[NameExpense]] = defaultdict(list)

        for share in expense_members:
            grouped[share.expense.event.name].append(
                NameExpense(
                    uid=share.expense.uid,
                    name=share.expense.name,
                    currency=share.expense.currency,
                    amount=float(share.amount),
                    status=share.status_paid,
                    created_at=share.expense.created_at,
                    deleted=share.deleted,
                )
            )
        result: list[ExpenseEvent] = [
            ExpenseEvent(event=event_name, expense=expenses)
            for event_name, expenses in grouped.items()
        ]
        return result

    @staticmethod
    def list_member_balances(group: Group, currency: str):
        return GroupMemberBalance.objects.filter(
            group=group, currency=currency
        ).values_list("user__uid", "balance")

    @staticmethod
    def delete_restructure_debt(group: Group, currency: str):
        return RestructureDebt.objects.filter(group=group, currency=currency).delete()

    @staticmethod
    def create_restructure_debt(restructure_debt: List[RestructureDebt]):
        RestructureDebt.objects.bulk_create(restructure_debt)

    @staticmethod
    def delete_group_members(group_members: List[GroupMember]):
        return GroupMember.objects.filter(
            uid__in=[gm.uid for gm in group_members]
        ).delete()

    @staticmethod
    def update_group_leader(group: Group, new_leader: TUser):
        group.leader = new_leader
        group.save()
        return

    @staticmethod
    def list_members_for_balance(group: Group):
        return GroupMember.objects.filter(group=group, status="ACTIVE").order_by(
            "user__full_name"
        )

    @staticmethod
    def get_groups_by_member(user: TUser):
        return Group.objects.filter(
            group_member_fk_group__user__uid=user.uid, status="ACTIVE"
        ).distinct()

    @staticmethod
    def get_balances_by_group_and_member(
        user: TUser,
        currency: str,
        filter: FilterNameSchema,
        order_by: OrderByNameAndUpdatedAtSchema,
    ):
        members_qs = (
            GroupMember.objects.filter(status="ACTIVE")
            .annotate(
                balance=Coalesce(
                    Sum(
                        Case(
                            # member là creditor, user hiện tại là debtor
                            When(
                                Q(
                                    group__restructure_debt_fk_group__creditor=F(
                                        "user"
                                    ),
                                    group__restructure_debt_fk_group__currency=currency,
                                )
                                & Q(group__restructure_debt_fk_group__debtor=user),
                                then=F("group__restructure_debt_fk_group__value"),
                            ),
                            # member là debtor, user hiện tại là creditor
                            When(
                                Q(
                                    group__restructure_debt_fk_group__debtor=F("user"),
                                    group__restructure_debt_fk_group__currency=currency,
                                )
                                & Q(group__restructure_debt_fk_group__creditor=user),
                                then=-F("group__restructure_debt_fk_group__value"),
                            ),
                            default=Value(0, output_field=DecimalField()),
                            output_field=DecimalField(),
                        )
                    ),
                    Value(0, output_field=DecimalField()),
                ),
                has_debt=Case(
                    When(~Q(balance=0), then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
                abs_balance=Abs(F("balance"), output_field=DecimalField()),
            )
            .order_by("-has_debt", "-abs_balance")[:10]
        )
        query = (
            Group.objects.filter(group_member_fk_group__user=user)
            .exclude(status="DELETED")
            .prefetch_related(
                Prefetch(
                    "group_member_fk_group",
                    queryset=members_qs,
                    to_attr="group_members",
                )
            )
        )
        if filter:
            query = query.filter(filter.get_filter_expression())

        if order_by:
            query = query.order_by(order_by.get_order_by_expression())
        return query

    @staticmethod
    def restructured_debt(user: TUser, group: Group, currency: Optional[str]):
        if currency:
            return RestructureDebt.objects.filter(
                (Q(creditor=user) | Q(debtor=user))
                & Q(group=group)
                & Q(currency=currency)
            ).select_related("debtor", "creditor")
        return RestructureDebt.objects.filter(
            (Q(creditor=user) | Q(debtor=user)) & Q(group=group)
        ).select_related("debtor", "creditor")

    @staticmethod
    def group_report(group: Group):
        return GroupMemberBalance.objects.filter(group=group).values_list(
            "user__uid", "balance"
        )

    @staticmethod
    def get_member_spending(group: Group, total_amount: Decimal):
        return (
            UserSharesInExpense.objects.filter(
                expense__event__group=group, deleted="ACTIVE"
            )
            .values(full_name=F("user__full_name"))
            .annotate(
                spending_amount=Sum(
                    Case(
                        When(amount__lt=0, then=F("amount")),
                        default=-F("payer_amount"),
                        output_field=DecimalField(),
                    )
                ),
            )
            .annotate(
                percent=ExpressionWrapper(
                    Round(-(F("spending_amount") / total_amount) * 100, 2),
                    output_field=DecimalField(max_digits=5, decimal_places=2),
                )
            )
            .values("full_name", "percent")
        )

    @staticmethod
    def get_member_count(
        group: Group,
    ):
        return GroupMember.objects.filter(group=group, status="ACTIVE").count()

    @staticmethod
    def total_mutual_groups(user: TUser, friend: TUser):
        return GroupMember.objects.filter(
            user=user,
            group__group_member_fk_group__user=friend,
            group__group_member_fk_group__status="ACTIVE",
            status="ACTIVE",
        ).count()

    @staticmethod
    def total_debt_between_two_people(user: TUser, friend: TUser):
        return (
            RestructureDebt.objects.filter(
                Q(creditor=user, debtor=friend) | Q(debtor=user, creditor=friend),
                status="ACTIVE",
            )
            .annotate(
                signed_value=Case(
                    When(creditor=user, then=F("value")),
                    When(debtor=user, then=-F("value")),
                    default=Value(0),
                    output_field=DecimalField(),
                )
            )
            .aggregate(total_debt=Sum("signed_value"))
            .get("total_debt")
            or 0
        )

    @staticmethod
    def friend_debt(user: TUser, friend: TUser):
        return (
            RestructureDebt.objects.filter(
                Q(creditor=user, debtor=friend) | Q(debtor=user, creditor=friend),
                status="ACTIVE",
            )
            .select_related("debtor", "creditor", "group")
            .order_by("-value")
        )
