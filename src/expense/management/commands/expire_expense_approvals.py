"""
python manage.py expire_expense_approvals
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import now

from expense.models import ExpenseApproval
from expense.queries import Query
from expense.service import Service
from utils.enums import ExpenseApprovalStatusEnum


class Command(BaseCommand):
    help = "Expire pending expense approvals that have passed their 24-hour deadline"

    def handle(self, *args, **options):
        # Find expenses that still have a pending_action and have overdue approvals
        expired_expense_uids = (
            ExpenseApproval.objects.filter(
                status=ExpenseApprovalStatusEnum.PENDING,
                expires_at__lt=now(),
            )
            .values_list("expense_id", flat=True)
            .distinct()
        )

        service = Service()
        query = Query()
        count = 0

        for expense_uid in expired_expense_uids:
            expense = query.get_expense_by_uid(expense_uid=expense_uid)
            if not expense or not expense.pending_action:
                continue
            try:
                with transaction.atomic():
                    service._check_and_finalize_approval(expense=expense)
                count += 1
            except Exception as exc:
                self.stderr.write(f"Error processing expense {expense_uid}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(f"Processed {count} expired expense approval(s).")
        )
