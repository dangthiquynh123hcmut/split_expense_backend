from enum import unique

from django.db.models import TextChoices


@unique
class RoleEnum(TextChoices):
    ADMIN = "ADMIN", "admin"
    USER = "USER", "user"
    SUPERUSER = "SUPERUSER", "superuser"
