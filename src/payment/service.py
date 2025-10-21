import random

from django.db import transaction

from authenticate.queries import Query as Auth_Query
from user.queries import Query as User_Query
from utils.types import AuthenticatedRequest
from wallet.orm.deposit import DepositORM

from .config import VNPayConfig
from .schemas import PaymentRequest
from .utils import build_payment_url, get_client_ip, hmac_sha512


class Service:
    def __init__(self):
        self.vn_pay_config = VNPayConfig()
        self.user_query = User_Query()
        self.auth_query = Auth_Query()
        self.deposit_query = DepositORM()

    def create_payment_url(
        self, request: AuthenticatedRequest, payload: PaymentRequest
    ):
        amount = int(payload.amount) * 100
        bank_code = payload.bank_code
        currency = payload.currency
        vnp_params = self.vn_pay_config.get_vnp_config()
        vnp_params["vnp_Amount"] = str(amount)

        if bank_code:
            vnp_params["vnp_BankCode"] = bank_code
        if currency:
            vnp_params["vnp_CurrCode"] = currency
            vnp_params["vnp_TxnRef"] = f"{random.randint(10000, 99999)}{currency}"
        vnp_params["vnp_OrderInfo"] = str(request.user.uid)
        vnp_params["vnp_IpAddr"] = get_client_ip(request)

        query_url = build_payment_url(vnp_params, sort=True)
        hash_data = build_payment_url(vnp_params, sort=True)
        vnp_secure_hash = hmac_sha512(self.vn_pay_config.secret_key, hash_data)

        query_url += f"&vnp_SecureHash={vnp_secure_hash}"
        payment_url = f"{self.vn_pay_config.vnp_pay_url}?{query_url}"

        return {"payment_url": payment_url}

    @transaction.atomic
    def create_deposit(self, user: AuthenticatedRequest, amount: float, currency: str):
        self.user_query.update_balance(user=user, amount=amount)
        self.deposit_query.add_deposit_history(
            amount=amount, user=user, currency=currency
        )
        return
