import uuid
from uuid import UUID

from django.conf import settings
from django.core.cache import cache


def generate_transfer_token(user_uid: UUID, amount: float) -> str:
    token = str(uuid.uuid4())
    key = f"transfer_token:{user_uid}:{token}"
    data = {"user_uid": user_uid, "amount": amount}
    cache.set(key, data, timeout=settings.OTP_LIFETIME * 6000)
    return token


def verify_transfer_token(user_uid: UUID, token: str, amount: float):
    key = f"transfer_token:{user_uid}:{token}"
    data = cache.get(key)
    if not data:
        return False
    if data["user_uid"] != user_uid:
        return False
    if data["amount"] != amount:
        return False
    cache.delete(key)
    return True
