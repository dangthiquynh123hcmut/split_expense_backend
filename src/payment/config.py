import random
from datetime import datetime, timedelta, timezone

from django.conf import settings


class VNPayConfig:
    def __init__(self):
        self.vnp_version = settings.VNPAY_VERSION
        self.vnp_command = settings.VNPAY_COMMAND
        self.vnp_tmn_code = settings.VNPAY_CONFIG["vnp_TmnCode"]
        self.secret_key = settings.VNPAY_CONFIG["vnp_HashSecret"]
        self.order_type = settings.ORDER_TYPE
        self.vnp_return_url = settings.VNPAY_CONFIG["vnp_ReturnUrl"]
        self.vnp_pay_url = settings.VNPAY_CONFIG["vnp_Url"]

    def get_vnp_config(self):
        now = datetime.now(timezone(timedelta(hours=7)))
        vnp_create_date = now.strftime("%Y%m%d%H%M%S")
        vnp_expire_date = (
            now + timedelta(minutes=int(settings.VNPAY_LIFETIME))
        ).strftime("%Y%m%d%H%M%S")

        return {
            "vnp_Version": self.vnp_version,
            "vnp_Command": self.vnp_command,
            "vnp_TmnCode": self.vnp_tmn_code,
            "vnp_TxnRef": f"{random.randint(10000, 99999)}",
            "vnp_OrderType": self.order_type,
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": self.vnp_return_url,
            "vnp_CreateDate": vnp_create_date,
            "vnp_ExpireDate": vnp_expire_date,
        }
