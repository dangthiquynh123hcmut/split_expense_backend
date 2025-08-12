from datetime import datetime


def generate_code_visit(date_visit: datetime, subject_code: str) -> str:
    timestamp_str = date_visit.strftime("%y%m%d%H%M")
    return f"{subject_code}-{timestamp_str}"
