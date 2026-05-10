import random
import string
from datetime import datetime
from uuid import UUID


def generate_code_transfer(user: UUID) -> str:
    timestamp_str = datetime.now().strftime("%y%m%d%H%M%S%f")[:14]
    random_part = "".join(random.choices(string.digits, k=6))
    user_prefix = str(user)[:4].upper()
    return f"{user_prefix}-{timestamp_str}-{random_part}"
