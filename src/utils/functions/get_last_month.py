from datetime import datetime, timedelta


def get_last_month(today: datetime):
    start_this_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    end_last_month = start_this_month - timedelta(microseconds=1)

    start_last_month = end_last_month.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    return start_last_month, end_last_month
