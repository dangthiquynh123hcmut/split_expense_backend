import asyncio
import uuid
from uuid import UUID

from django.conf import settings
from django.core.cache import cache


async def generate_transfer_token_async(user_uid: UUID, amount: float) -> str:
    token = str(uuid.uuid4())
    key = f"transfer_token:{user_uid}:{token}"
    data = {"user_uid": str(user_uid), "amount": amount}
    timeout = settings.OTP_LIFETIME * 60

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, cache.set, key, data, timeout)
    return token


async def verify_transfer_token_async(
    user_uid: UUID, token: str, amount: float
) -> bool:
    key = f"transfer_token:{user_uid}:{token}"

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, cache.get, key)

    if not data:
        return False

    if str(data.get("user_uid")) != str(user_uid):
        return False
    if data.get("amount") != amount:
        return False

    await loop.run_in_executor(None, cache.delete, key)
    return True
