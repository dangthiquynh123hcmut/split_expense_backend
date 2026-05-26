from collections import defaultdict
from decimal import Decimal
from typing import Any, DefaultDict, Dict, List
from uuid import UUID

from django.db.models import DecimalField, ExpressionWrapper, F, Q
from django.db.models.functions import Round
from django.utils.timezone import now

from attachment.schemas.responses import AttachmentResponse
from event.models import Event, EventMember, EventMemberBalance, EventRestructureDebt
from event.schemas.request import EventUpdateRequest
from expense.models import UserSharesInExpense
from group.models import Group
from utils.functions.get_last_month import get_last_month
from utils.schemas.filter_and_order_by import (
    FilterEventAdminSchema,
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
)
from utils.types import TUser


class Query:
    @staticmethod
    def create_event(user: TUser, **kwargs):
        return Event.objects.create(creator=user, **kwargs)

    @staticmethod
    def create_event_members(event_members: List[EventMember]):
        EventMember.objects.bulk_create(event_members)
        return

    @staticmethod
    def get_event(event_uid: UUID):
        try:
            return Event.objects.get(uid=event_uid, status="ACTIVE")
        except Event.DoesNotExist:
            return None

    @staticmethod
    def get_event_has_user(user: TUser, event: Event):
        try:
            return EventMember.objects.get(user=user, event=event, status="ACTIVE")
        except EventMember.DoesNotExist:
            return None

    @staticmethod
    def update_event(event: Event, data: EventUpdateRequest):
        if event:
            for attr, value in data.dict().items():
                setattr(event, attr, value)
            event.save()
        return event

    @staticmethod
    def leave_event(user: TUser, event: Event):
        return EventMember.objects.filter(user=user, event=event).update(
            status="DELETED"
        )

    @staticmethod
    def delete_event(event_uid: UUID):
        return Event.objects.filter(uid=event_uid).update(status="DELETED")

    @staticmethod
    def list_event_members(
        event: Event,
        filter: FilterFullNameSchema,
        order_by: OrderByFullNameAndUpdatedAtSchema,
    ):
        query = EventMember.objects.filter(event=event, status="ACTIVE").annotate(
            event_member_uid=F("uid"),
            user_uid=F("user__uid"),
            full_name=F("user__full_name"),
            avatar_url=F("user__avatar_url"),
        )
        if filter and filter.search:
            query = query.filter(filter.filter_search(filter.search))

        if order_by:
            query = query.annotate(full_name=F("user__full_name")).order_by(
                order_by.get_order_by_expression()
            )
        return query

    @staticmethod
    def get_detail_event(event_uid: UUID):
        return Event.objects.filter(uid=event_uid, status="ACTIVE").first()

    @staticmethod
    def join_event(user: TUser, event: Event):
        return EventMember.objects.create(user=user, event=event)

    @staticmethod
    def list_events_groups(user: TUser, filter: FilterNameSchema):
        queryset = (
            EventMember.objects.filter(
                user=user, status="ACTIVE", event__status="ACTIVE"
            )
            .select_related("event__group__avatar_url")
            .annotate(
                event_uid=F("event__uid"),
                event_name=F("event__name"),
                event_description=F("event__description"),
                event_start=F("event__event_start"),
                event_end=F("event__event_end"),
                group_uid=F("event__group__uid"),
                group_name=F("event__group__name"),
                group_avatar_url=F("event__group__avatar_url"),
            )
        )
        if filter and filter.search:
            queryset = queryset.filter(filter.filter_search(filter.search))
        grouped: DefaultDict[str, Dict[str, Any]] = defaultdict(
            lambda: {"group_name": "", "group_avatar_url": "", "list_event": []}
        )

        for m in queryset:
            grouped[m.group_uid]["group_name"] = m.group_name
            avatar = m.event.group.avatar_url
            grouped[m.group_uid]["group_avatar_url"] = (
                AttachmentResponse.from_orm(avatar) if avatar else None
            )
            grouped[m.group_uid]["list_event"].append(
                {
                    "event_uid": m.event_uid,
                    "event_name": m.event_name,
                    "event_description": m.event_description,
                    "event_start": m.event_start,
                    "event_end": m.event_end,
                }
            )
        return list(grouped.values())

    @staticmethod
    def events_attended_in_group(user: TUser, group: Group):
        return EventMember.objects.filter(
            user=user, event__group=group, status="ACTIVE"
        ).count()

    @staticmethod
    def total_events_in_group(group: Group):
        return Event.objects.filter(group=group, status="ACTIVE").count()

    @staticmethod
    def total_mutual_events(user: TUser, friend: TUser):
        return EventMember.objects.filter(
            user=user,
            event__event_member_fk_event__user=friend,
            event__event_member_fk_event__status="ACTIVE",
            status="ACTIVE",
        ).count()

    @staticmethod
    def total_event_members(event: Event):
        return EventMember.objects.filter(event=event, status="ACTIVE").count()

    @staticmethod
    def get_event_spending(event: Event, total_amount: Decimal, currency: str = "VND"):
        return (
            UserSharesInExpense.objects.filter(
                expense__event=event, deleted="ACTIVE", expense__currency=currency
            )
            .values("user__full_name")
            .annotate(
                percent=Round(
                    ExpressionWrapper(
                        (F("amount") / total_amount) * 100,
                        output_field=DecimalField(max_digits=5, decimal_places=2),
                    ),
                    2,
                )
            )
            .values(full_name=F("user__full_name"), percent=F("percent"))
        )

    @staticmethod
    def get_event_members(event: Event):
        return EventMember.objects.filter(event=event, status="ACTIVE")

    @staticmethod
    def count_events():
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        return Event.objects.filter(
            created_at__date__gte=start_this_month
        ).count(), Event.objects.filter(
            created_at__date__gte=start_last_month, created_at__date__lte=end_last_month
        ).count()

    @staticmethod
    def count_event_members():
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        return EventMember.objects.filter(
            created_at__date__gte=start_this_month
        ).count(), EventMember.objects.filter(
            created_at__date__gte=start_last_month, created_at__date__lte=end_last_month
        ).count()

    @staticmethod
    def count_active_events():
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        return Event.objects.filter(
            status="ACTIVE",
            event_end__gte=now(),
            created_at__date__gte=start_this_month,
        ).count(), Event.objects.filter(
            status="ACTIVE",
            event_end__gte=now(),
            created_at__date__lte=end_last_month,
            created_at__date__gte=start_last_month,
        ).count()

    @staticmethod
    def count_finished_events():
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        return Event.objects.filter(
            status="ACTIVE", event_end__lt=now(), created_at__date__gte=start_this_month
        ).count(), Event.objects.filter(
            status="ACTIVE",
            event_end__lt=now(),
            created_at__date__lte=end_last_month,
            created_at__date__gte=start_last_month,
        ).count()

    @staticmethod
    def list_events_admin(filter: FilterEventAdminSchema):
        return Event.objects.filter(filter.get_filter_expression())

    @staticmethod
    def list_event_members_admin(event_uid: UUID, filter: FilterFullNameSchema):
        return (
            EventMember.objects.filter(event_id=event_uid)
            .filter(filter.filter_search(filter.search))
            .annotate(
                event_member_uid=F("uid"),
            )
        )

    @staticmethod
    def deactivate_event(event_uid: UUID):
        Event.objects.filter(
            uid=event_uid,
        ).update(status="INACTIVE")

    @staticmethod
    def active_event(event_uid: UUID):
        Event.objects.filter(
            uid=event_uid,
        ).update(status="ACTIVE")

    @staticmethod
    def close_event(event_uid: UUID):
        Event.objects.filter(uid=event_uid).update(status="CLOSED")

    @staticmethod
    def close_expired_events():
        today = now().date()
        expired = Event.objects.filter(status="ACTIVE", event_end__lt=today)
        event_uids = list(expired.values_list("uid", flat=True))
        if event_uids:
            expired.update(status="CLOSED")
            EventMemberBalance.objects.filter(event_id__in=event_uids).delete()
        return len(event_uids)

    @staticmethod
    def delete_event_member_balance(event: Event):
        EventMemberBalance.objects.filter(event=event).delete()

    @staticmethod
    def list_event_member_balances(event: Event, currency: str):
        shares = UserSharesInExpense.objects.filter(
            expense__event=event,
            expense__currency=currency,
            deleted="ACTIVE",
        ).values("user__uid", "amount", "receiver_amount")

        balance_map: DefaultDict = defaultdict(Decimal)
        for share in shares:
            uid = share["user__uid"]
            balance_map[uid] += (share["receiver_amount"] or Decimal("0")) - (
                share["amount"] or Decimal("0")
            )

        return [(uid, balance) for uid, balance in balance_map.items() if balance != 0]

    @staticmethod
    def delete_event_restructure_debt(event: Event, currency: str):
        return EventRestructureDebt.objects.filter(
            event=event, currency=currency
        ).delete()

    @staticmethod
    def create_event_restructure_debt(restructure_debts: List[EventRestructureDebt]):
        EventRestructureDebt.objects.bulk_create(restructure_debts)

    @staticmethod
    def update_event_restructure_debt(
        debtor: TUser, creditor: TUser, event: Event, amount: Decimal, currency: str
    ):
        EventRestructureDebt.objects.filter(
            event=event, debtor=debtor, creditor=creditor, currency=currency
        ).delete()

    @staticmethod
    def update_event_member_balance(
        debtor: TUser, creditor: TUser, event: Event, amount: Decimal, currency: str
    ):
        EventMemberBalance.objects.filter(
            event=event, user=debtor, currency=currency
        ).update(balance=F("balance") + amount)

        EventMemberBalance.objects.filter(
            event=event, user=creditor, currency=currency
        ).update(balance=F("balance") - amount)

    def get_event_balance(self, event: Event, user: TUser):
        return EventRestructureDebt.objects.filter(
            Q(debtor=user) | Q(creditor=user), event=event
        )

    @staticmethod
    def get_event_restructure_debts_by_event(
        debtor: TUser, creditor: TUser, event: "Event", currency: str
    ):
        return (
            EventRestructureDebt.objects.select_for_update()
            .filter(
                debtor=debtor,
                creditor=creditor,
                event=event,
                currency=currency,
                value__gt=0,
            )
            .select_related("event")
        )

    @staticmethod
    def get_event_restructure_debts_between_users(
        debtor: TUser, creditor: TUser, group: Group, currency: str
    ):
        return (
            EventRestructureDebt.objects.select_for_update()
            .filter(
                debtor=debtor,
                creditor=creditor,
                event__group=group,
                currency=currency,
                value__gt=0,
            )
            .select_related("event")
        )

    @staticmethod
    def settle_event_restructure_debt(
        debt: "EventRestructureDebt",
        amount: Decimal,
        debtor: TUser,
        creditor: TUser,
        currency: str,
    ):
        EventRestructureDebt.objects.filter(uid=debt.uid).update(
            value=F("value") - amount
        )
        EventRestructureDebt.objects.filter(uid=debt.uid, value__lte=0).delete()

        EventMemberBalance.objects.filter(
            event=debt.event, user=debtor, currency=currency
        ).update(balance=F("balance") + amount)

        EventMemberBalance.objects.filter(
            event=debt.event, user=creditor, currency=currency
        ).update(balance=F("balance") - amount)

    def delete_event_members(self, event: Event):
        return EventMember.objects.filter(event=event).update(status="DELETED")
