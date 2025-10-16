import hashlib
import hmac
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
