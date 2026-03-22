from django.conf import settings
from django.db import models

from utils.enums import CurrencyEnum
from utils.models.base_model import BaseModel


class PayOSOrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PAID = "PAID", "Paid"
    CANCELLED = "CANCELLED", "Cancelled"


class PayOSOrder(BaseModel):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="payos_order_fk_user",
    )
    order_code = models.BigIntegerField(unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(
        max_length=20,
        choices=CurrencyEnum.choices,
        default=CurrencyEnum.VND,
    )
    description = models.CharField(max_length=25, null=True)
    status = models.CharField(
        max_length=10,
        choices=PayOSOrderStatus.choices,
        default=PayOSOrderStatus.PENDING,
    )
    checkout_url = models.URLField(max_length=500)
    payment_link_id = models.CharField(max_length=255, default="")
