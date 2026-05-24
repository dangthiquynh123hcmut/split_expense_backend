import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class EventConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "event"

    def ready(self):
        self._start_scheduler()

    @staticmethod
    def _start_scheduler():
        try:
            from apscheduler.schedulers.background import (
                BackgroundScheduler,  # type: ignore
            )
            from apscheduler.triggers.cron import CronTrigger  # type: ignore

            from event.queries import Query as EventQuery  # type: ignore

            scheduler = BackgroundScheduler()
            scheduler.add_job(
                EventQuery.close_expired_events,
                trigger=CronTrigger(hour=0, minute=5),
                id="close_expired_events",
                replace_existing=True,
            )
            scheduler.start()
            logger.info("Scheduler started: close_expired_events runs daily at 00:05.")
        except ImportError:
            logger.warning(
                "apscheduler not installed. Automatic event closing is disabled. "
                "Run 'python manage.py close_expired_events' manually or via an external cron."
            )
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to start scheduler: %s", exc)
