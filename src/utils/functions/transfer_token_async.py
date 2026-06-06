from uuid import UUID

from django.conf import settings
from django.utils.timezone import now

from wallet.models import TransferToken


TRANSFER_TOKEN_EXPIRY_MINUTES = settings.TRANSFER_TOKEN_LIFETIME


async def generate_transfer_token_async(user_uid: UUID, amount: float) -> str:
    """Store transfer token directly in DB instead of Redis."""
    token_obj = await TransferToken.objects.acreate(
        user_id=user_uid,
        amount=amount,
    )
    return str(token_obj.token)


async def verify_transfer_token_async(
    user_uid: UUID, token: str, amount: float
) -> bool:
    """Verify transfer token, enforce N-min expiry, then delete on success."""
    try:
        token_obj = await TransferToken.objects.aget(
            user_id=user_uid,
            token=token,
        )
    except TransferToken.DoesNotExist:
        return False

    # Check expiry (N minutes from creation)
    age = (now() - token_obj.created_at).total_seconds()
    if age > TRANSFER_TOKEN_EXPIRY_MINUTES * 60:
        await token_obj.adelete()
        from exceptions.wallet import TransferTokenExpired

        raise TransferTokenExpired

    # Validate amount
    if float(token_obj.amount) != float(amount):
        return False

    # Token is valid and used → delete it
    await token_obj.adelete()
    return True
