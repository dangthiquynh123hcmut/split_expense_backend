from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from authenticate.models import AuthenticateToken, RefreshToken


class Command(BaseCommand):
    help = "Cleans up expired authentication and refresh tokens."

    def handle(self, *args, **options):
        now = timezone.now()

        access_tokens_deleted, _ = AuthenticateToken.objects.filter(
            expires_at__lt=now
        ).delete()

        refresh_tokens_deleted, _ = RefreshToken.objects.filter(
            Q(expires_at__lt=now) | Q(is_blacklisted=True)
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully cleaned up {access_tokens_deleted or 0} access tokens and "
                f"{refresh_tokens_deleted or 0} refresh tokens."
            )
        )
