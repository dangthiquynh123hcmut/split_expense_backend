from django.db.models import CharField, Value

from authenticate.models import User
from wallet.models import WalletDeposit, Withdraw


class TransactionORM:
    @staticmethod
    def get_external_transaction_history(user: User):
        deposits = (
            WalletDeposit.objects.filter(user=user)
            .annotate(type=Value("deposit", output_field=CharField()))
            .values("uid", "type", "amount", "currency", "code", "date")
        )

        withdraws = (
            Withdraw.objects.filter(user=user)
            .annotate(
                type=Value("withdraw", output_field=CharField()),
                currency=Value(user.currency, output_field=CharField()),
            )
            .values("uid", "type", "amount", "currency", "code", "date")
        )

        return deposits.union(withdraws).order_by("-date")
