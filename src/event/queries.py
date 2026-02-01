from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Any, DefaultDict, Dict, List
from uuid import UUID

from django.db.models import DecimalField, ExpressionWrapper, F
from django.db.models.functions import Round
from django.utils.timezone import now

from attachment.schemas.responses import AttachmentResponse
from event.models import Event, EventMember
from event.schemas.request import EventUpdateRequest
from expense.models import UserSharesInExpense
from group.models import Group
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
            EventMember.objects.filter(user=user, status="ACTIVE")
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
        yesterday = now().date() - timedelta(days=1)

        return Event.objects.count(), Event.objects.filter(
            created_at__date__lte=yesterday
        ).count()

    @staticmethod
    def count_event_members():
        yesterday = now().date() - timedelta(days=1)

        return EventMember.objects.count(), EventMember.objects.filter(
            created_at__date__lte=yesterday
        ).count()

    @staticmethod
    def count_active_events():
        yesterday = now().date() - timedelta(days=1)

        return Event.objects.filter(
            status="ACTIVE", event_end__gte=now()
        ).count(), Event.objects.filter(
            status="ACTIVE", event_end__gte=now(), created_at__date__lte=yesterday
        ).count()

    @staticmethod
    def count_finished_events():
        yesterday = now().date() - timedelta(days=1)

        return Event.objects.filter(
            status="ACTIVE", event_end__lt=now()
        ).count(), Event.objects.filter(
            status="ACTIVE", event_end__lt=now(), created_at__date__lte=yesterday
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
