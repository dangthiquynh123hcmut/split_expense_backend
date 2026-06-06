from uuid import UUID

from django.conf import settings
from django.utils.timezone import now

from wallet.models import TransferToken


TRANSFER_TOKEN_EXPIRY_MINUTES = settings.TRANSFER_TOKEN_LIFETIME


def generate_transfer_token(user_uid: UUID, amount: float) -> str:
    """Store transfer token directly in DB instead of Redis."""
    token_obj = TransferToken.objects.create(
        user_id=user_uid,
        amount=amount,
    )
    return str(token_obj.token)


def verify_transfer_token(user_uid: UUID, token: str, amount: float) -> bool:
    """Verify transfer token, enforce 2-min expiry, then delete on success."""
    try:
        token_obj = TransferToken.objects.get(
            user_id=user_uid,
            token=token,
        )
    except TransferToken.DoesNotExist:
        return False

    # Check expiry (N minutes from creation)
    age = (now() - token_obj.created_at).total_seconds()
    if age > TRANSFER_TOKEN_EXPIRY_MINUTES * 60:
        token_obj.delete()
        from exceptions.wallet import TransferTokenExpired

        raise TransferTokenExpired

    # Validate amount
    if float(token_obj.amount) != float(amount):
        return False

    # Token is valid and used → delete it
    token_obj.delete()
    return True
