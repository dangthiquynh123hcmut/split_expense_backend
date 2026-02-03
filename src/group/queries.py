from decimal import Decimal
from typing import List
from uuid import UUID

from channels.db import database_sync_to_async
from django.db.models import (
    Case,
    Count,
    DecimalField,
    F,
    IntegerField,
    Prefetch,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Abs, Coalesce
from django.utils.timezone import now

from attachment.models import Attachment
from authenticate.models import User
from event.models import Event
from expense.models import Expense, UserSharesInExpense
from expense.schemas.response import NameExpense
from utils.enums import StatusEnum
from utils.functions.get_last_month import get_last_month
from utils.schemas.filter_and_order_by import (
    FilterCurrencySchema,
    FilterFullNameSchema,
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
            return False

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
    def update_currency_in_group_member_balance(
        group: Group, old_currency: str, new_currency: str
    ):
        return GroupMemberBalance.objects.filter(
            group=group, currency=old_currency
        ).update(currency=new_currency)

    @staticmethod
    def get_users_in_group_member_balance(group: Group, currency: str):
        return GroupMemberBalance.objects.filter(
            group=group, currency=currency
        ).values_list("user__uid", flat=True)

    @staticmethod
    def create_group_member_balance(group_member_balance: List[GroupMemberBalance]):
        return GroupMemberBalance.objects.bulk_create(group_member_balance)

    @staticmethod
    def update_total_amount(
        group: Group, expense_members: List[UserSharesInExpense], currency: str
    ):
        whens = []
        users = []

        for em in expense_members:
            users.append(em.user)
            whens.append(When(user=em.user, then=F("balance") + em.amount))

        return GroupMemberBalance.objects.filter(
            group=group, user__in=users, currency=currency
        ).update(balance=Case(*whens, default=F("balance")))

    @staticmethod
    def list_expenses_in_a_group(
        user: User,
        group: Group,
        status: str,
    ):
        expenses = Expense.objects.filter(event__group=group, status=status)
        user_shares = UserSharesInExpense.objects.filter(
            expense__event__group=group,
            user=user,
            deleted=status,
        ).select_related("expense")

        user_share_map = {share.expense_id: share for share in user_shares}
        expenses_result = []

        for expense in expenses:
            share = user_share_map.get(expense.uid)
            if share:
                amount_value = (
                    share.receiver_amount
                    if (share.receiver_amount) > 0  # type: ignore
                    else -share.amount
                )
                amount = float(amount_value)  # type: ignore
            else:
                amount = 0.0
            expenses_result.append(
                NameExpense(
                    uid=expense.uid,
                    name=expense.name,
                    currency=expense.currency,
                    amount=amount,
                    created_at=expense.created_at,
                    status=expense.status,
                    event=expense.event.name,
                    category=expense.category,
                )
            )
        return expenses_result

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
    def update_group_leader(group: Group, leader: TUser):
        group.leader = leader
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
                                then=-F("group__restructure_debt_fk_group__value"),
                            ),
                            # member là debtor, user hiện tại là creditor
                            When(
                                Q(
                                    group__restructure_debt_fk_group__debtor=F("user"),
                                    group__restructure_debt_fk_group__currency=currency,
                                )
                                & Q(group__restructure_debt_fk_group__creditor=user),
                                then=F("group__restructure_debt_fk_group__value"),
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
    def restructured_debt(user: TUser, group: Group, filter: FilterCurrencySchema):
        if filter.currency:
            return RestructureDebt.objects.filter(
                (Q(creditor=user) | Q(debtor=user))
                & Q(group=group)
                & Q(currency=filter.currency)
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
    def get_member_spending(group: Group, total_amount: Decimal, currency: str = "VND"):
        user_totals = (
            UserSharesInExpense.objects.filter(
                expense__event__group=group,
                deleted="ACTIVE",
                expense__currency=currency,
            )
            .values("user__uid", "user__full_name")
            .annotate(total_user_amount=Sum("amount"))
        )

        result = []
        for user_data in user_totals:
            percent = (
                (user_data["total_user_amount"] / total_amount * 100)
                if total_amount > 0
                else 0
            )
            result.append(
                {
                    "full_name": user_data["user__full_name"],
                    "percent": round(percent, 2),
                    "amount": user_data["total_user_amount"],
                }
            )

        return result

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
            group__status="ACTIVE",
            group__group_member_fk_group__group__status="ACTIVE",
        ).count()

    @staticmethod
    def total_debt_between_two_people(user: TUser, friend: TUser):
        return (
            RestructureDebt.objects.filter(
                Q(creditor=user, debtor=friend) | Q(debtor=user, creditor=friend)
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
            )
            .select_related("debtor", "creditor", "group")
            .order_by("-value")
        )

    @staticmethod
    def update_balance_in_group(
        user: TUser, group: Group, amount: Decimal, currency: str
    ):
        GroupMemberBalance.objects.filter(
            group=group, user=user, currency=currency
        ).update(balance=F("balance") - amount)

    @staticmethod
    def update_restructure_debt(
        debtor: TUser, creditor: TUser, group: Group, amount: Decimal, currency: str
    ):
        RestructureDebt.objects.filter(
            group=group, debtor=debtor, creditor=creditor, currency=currency
        ).update(value=F("value") - amount)

    @staticmethod
    @database_sync_to_async
    def get_user_group_uids(user: TUser):
        memberships = GroupMember.objects.filter(
            user=user, status=StatusEnum.ACTIVE
        ).select_related("group")
        return [str(m.group.uid) for m in memberships]

    @staticmethod
    @database_sync_to_async
    def get_group_member_tokens(group_uid: str, exclude_user_uid: str):
        group = Group.objects.get(uid=group_uid)
        member_qs = (
            GroupMember.objects.filter(group=group, status=StatusEnum.ACTIVE)
            .exclude(user_id=exclude_user_uid)
            .select_related("user")
        )
        return [
            {"user_uid": member.user.uid, "fcm_token": member.user.fcm_token}
            for member in member_qs
        ]

    @staticmethod
    def count_groups():
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return Group.objects.filter(
            created_at__gte=start_this_month
        ).count(), Group.objects.filter(
            created_at__gte=start_last_month, created_at__lte=end_last_month
        ).count()

    @staticmethod
    def count_members():
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return GroupMember.objects.filter(
            joined_at__gte=start_this_month
        ).count(), GroupMember.objects.filter(
            joined_at__gte=start_last_month, joined_at__lte=end_last_month
        ).count()

    @staticmethod
    def count_active_groups():
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        start_last_month, end_last_month = get_last_month(now())
        return Group.objects.filter(
            status="ACTIVE", created_at__gte=start_this_month
        ).count(), Group.objects.filter(
            status="ACTIVE",
            created_at__gte=start_last_month,
            created_at__lte=end_last_month,
        ).count()

    @staticmethod
    def deactivate_groups(group_uid: UUID):
        Group.objects.filter(
            uid=group_uid,
        ).update(status="INACTIVE")

    @staticmethod
    def active_groups(group_uid: UUID):
        Group.objects.filter(
            uid=group_uid,
        ).update(status="ACTIVE")

    @staticmethod
    def list_groups_admin(filter: FilterNameSchema):
        query = (
            Group.objects.all()
            .annotate(
                total_members=Count(
                    "group_member_fk_group",
                    filter=Q(group_member_fk_group__status="ACTIVE"),
                )
            )
            .select_related("leader")
        )
        if filter:
            query = query.filter(filter.get_filter_expression())
        return query

    def get_group_by_uid(self, group_uid: UUID):
        return Group.objects.filter(uid=group_uid).first()

    def total_groups_by_user(self, user_uid: UUID):
        return Group.objects.filter(
            group_member_fk_group__user__uid=user_uid, status="ACTIVE"
        ).count()

    def total_balances_by_user(self, user_uid: UUID):
        return (
            GroupMemberBalance.objects.filter(
                user__uid=user_uid, balance__gt=0
            ).aggregate(total_balance=Sum("balance"))["total_balance"]
            or 0
        )

    def list_participating_groups(
        self,
        user_uid: UUID,
        filter: FilterNameSchema,
    ):
        queryset = (
            Group.objects.filter(
                group_member_fk_group__user__uid=user_uid, status="ACTIVE"
            )
            .annotate(joined_at=F("group_member_fk_group__joined_at"))
            .distinct()
        )
        if filter:
            queryset = queryset.filter(filter.get_filter_expression())

        return queryset
