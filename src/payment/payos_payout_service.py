import uuid

import requests
from django.conf import settings

from exceptions.wallet import BankBinNotFound, PayOSPayoutFailed

from .utils import create_payos_payout_signature


BANK_BIN_MAP: dict[str, str] = {
    "ICB": "970415",  # VietinBank
    "VCB": "970436",  # Vietcombank
    "BIDV": "970418",  # BIDV
    "VBA": "970405",  # Agribank
    "OCB": "970448",  # OCB
    "MB": "970422",  # MBBank
    "TCB": "970407",  # Techcombank
    "ACB": "970416",  # ACB
    "VPB": "970432",  # VPBank
    "TPB": "970423",  # TPBank
    "STB": "970403",  # Sacombank
    "HDB": "970437",  # HDBank
    "VCCB": "970454",  # VietCapitalBank
    "SCB": "970429",  # SCB
    "VIB": "970441",  # VIB
    "SHB": "970443",  # SHB
    "EIB": "970431",  # EximBank
    "MSB": "970426",  # MSB (Maritime)
    "CAKE": "546034",  # CAKE
    "Ubank": "546035",  # Ubank
    "VTLMONEY": "971005",  # Viettel Money
    "VNPTMONEY": "971011",  # VNPT Money
    "SGICB": "970400",  # SaigonBank
    "BAB": "970409",  # BacABank
    "PVCB": "970412",  # PVCombank
    "NCB": "970419",  # NCB
    "SHBVN": "970424",  # Shinhan Bank VN
    "ABB": "970425",  # ABBank
    "VAB": "970427",  # VietABank
    "NAB": "970428",  # NamABank
    "PGB": "970430",  # PGBank
    "VIETBANK": "970433",  # VietBank
    "BVB": "970438",  # Baoviet Bank
    "SEAB": "970440",  # SeABank
    "COOPBANK": "970446",  # CoopBank
    "LPB": "970449",  # LPBank
    "KLB": "970452",  # KienlongBank
    "KBank": "668888",  # KBank Thailand
    "CITIBANK": "533948",  # Citibank
    "CBB": "970444",  # CB Bank
    "CIMB": "422589",  # CIMB
    "WVN": "970457",  # Woori Bank VN
    "GPB": "970408",  # GPBank
    "HLBVN": "970442",  # HongLeong Bank VN
    "HSBC": "458761",  # HSBC
    "UOB": "970458",  # UOB
    "SCVN": "970410",  # Standard Chartered VN
}


class PayOSPayoutService:
    def __init__(self):
        self.client_id = settings.PAYOS_CLIENT_ID_OUT
        self.api_key = settings.PAYOS_API_KEY_OUT
        self.checksum_key = settings.PAYOS_CHECKSUM_KEY_OUT
        self.payos_payout_url = settings.PAYOS_PAYOUT_URL

    def get_bank_bin(self, bank_code: str) -> str:
        bank_bin = BANK_BIN_MAP.get(bank_code)
        if not bank_bin:
            raise BankBinNotFound
        return bank_bin

    def create_payout(
        self,
        *,
        reference_id: str,
        amount: int,
        description: str,
        bank_code: str,
        account_number: str,
    ) -> dict:
        bank_bin = self.get_bank_bin(bank_code)

        payload = {
            "referenceId": reference_id,
            "amount": int(amount),
            "description": description,
            "toBin": bank_bin,
            "toAccountNumber": account_number,
        }

        signature = create_payos_payout_signature(
            secret_key=self.checksum_key,
            payload=payload,
        )

        # x-idempotency-key prevents duplicates on network retries
        idempotency_key = str(uuid.uuid4())
        headers = {
            "Content-Type": "application/json",
            "x-client-id": self.client_id,
            "x-api-key": self.api_key,
            "x-idempotency-key": idempotency_key,
            "x-signature": signature,
        }

        try:
            response = requests.post(
                self.payos_payout_url,
                json=payload,
                headers=headers,
                timeout=30,
            )
            response_data = response.json()
        except requests.RequestException as exc:
            raise PayOSPayoutFailed([str(exc)])

        if not response.ok or response_data.get("code") != "00":
            error_detail = response_data.get("desc", response.text)
            raise PayOSPayoutFailed([error_detail])

        return response_data.get("data", {})
