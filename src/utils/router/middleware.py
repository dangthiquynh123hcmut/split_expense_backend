import logging
import time
from datetime import datetime

from django.db import connection
from django.http import JsonResponse


LOGGER = logging.getLogger("django")


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

        # LOG IP ADDRESS
        LOGGER.info(
            "---------------------------------------------------------------\n"
            f"> Response: {response.status_code} {response.reason_phrase}\n"
            f"> IP Address: {request.META.get('REMOTE_ADDR')}\n"
            f"> Authenticator: {request.user}\n"
            f"> Running time: {ended_time - started_time}\n"
            f"> Number of queries: {ended_connection_queries - started_connection_queries}\n"
            "---------------------------------------------------------------"
        )

        if response.status_code == 404 and response.reason_phrase == "Not Found":
            return JsonResponse(
                {
                    "data": None,
                    "error_code": response.status_code,
                    "message_code": "PAGE_NOT_FOUND",
                    "message": "Page not found",
                    "current_time": datetime.now(),
                }
            )

        return response
