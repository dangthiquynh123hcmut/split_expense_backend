from django.core.management.base import BaseCommand

from event.queries import Query as EventQuery


class Command(BaseCommand):
    help = "Close all events whose event_end date has passed and delete their EventMemberBalance records."

    def handle(self, *args, **options):
        count = EventQuery.close_expired_events()
        self.stdout.write(self.style.SUCCESS(f"Closed {count} expired event(s)."))
