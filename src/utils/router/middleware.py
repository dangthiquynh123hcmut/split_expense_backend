import logging
import time

from django.db import connection

from api_log.models import ApiLog


LOGGER = logging.getLogger(__name__)


class APIMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api"):
            return self.get_response(request)

        started_time = time.time()
        started_connection_queries = len(connection.queries)

        response = self.get_response(request)

        ended_time = time.time()
        ended_connection_queries = len(connection.queries)

        response_time = ended_time - started_time
        num_queries = ended_connection_queries - started_connection_queries
        ip_address = request.META.get("REMOTE_ADDR")

        log_info = (
            "---------------------------------------------------------------\n"
            f"> Response: {response.status_code} {response.reason_phrase}\n"
            f"> IP Address: {ip_address}\n"
            f"> Authenticator: {request.user}\n"
            f"> Running time: {response_time}\n"
            f"> Number of queries: {num_queries}\n"
            "---------------------------------------------------------------"
        )
        LOGGER.info(log_info)

        try:
            ApiLog.objects.create(
                path=request.path,
                method_type=request.method,
                user=request.user if request.user.is_authenticated else None,
                status_code=response.status_code,
                response_time=response_time,
                log_message=log_info,
            )
        except Exception as e:
            LOGGER.error(f"Failed to save API log: {str(e)}")

        return response
