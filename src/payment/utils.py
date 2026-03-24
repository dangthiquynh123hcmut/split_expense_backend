import hashlib
import hmac
import json
import urllib.parse

from django.http import HttpRequest


def get_client_ip(request: HttpRequest):
    ip = request.META.get("HTTP_X_FORWARDED_FOR")
    if ip:
        ip = ip.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def hmac_sha512(key, data):
    return hmac.new(key.encode(), data.encode(), hashlib.sha512).hexdigest()


def build_payment_url(params: dict, sort: bool = True):
    sorted_params = sorted(params.items()) if sort else params.items()
    return "&".join(
        [f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_params]
    )


def create_payos_payout_signature(secret_key: str, payload: dict) -> str:
    sorted_keys = sorted(payload.keys())
    parts = []
    for key in sorted_keys:
        value = payload[key]
        if isinstance(value, (list, dict)):
            value = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        elif value is None:
            value = ""
        else:
            value = str(value)
        parts.append(
            f"{urllib.parse.quote(str(key), safe='')}={urllib.parse.quote(value, safe='')}"
        )
    query_string = "&".join(parts)
    return hmac.new(
        secret_key.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
