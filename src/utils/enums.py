from enum import Enum, unique

from django.db.models import TextChoices


@unique
class SubjectStatusEnum(TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    LOCKED = "LOCKED", "Locked"
    REMOVED = "REMOVED", "Removed"


@unique
class SubjectGenderEnum(TextChoices):
    MALE = "MALE", "Male"
    FEMALE = "FEMALE", "Female"
    OTHER = "OTHER", "Other"


@unique
class SortTypeEnum(Enum):
    ASC = "asc"
    DESC = "desc"
