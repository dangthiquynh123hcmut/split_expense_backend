import logging
import os
from datetime import datetime
from typing import Any

from django.http import HttpRequest, HttpResponse
from ninja.openapi.docs import Redoc
from ninja_extra import NinjaExtraAPI

from utils.router.authenticate import AuthBear
from utils.router.exception import get_handlers


logger = logging.getLogger("django")


class BaseAPI(NinjaExtraAPI):
    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("title", os.getenv("PRODUCT_NAME", ""))
        kwargs.setdefault("version", os.getenv("VERSION_NAME", ""))
        kwargs.setdefault("openapi_url", "openapi.json")
        kwargs.setdefault("docs_url", "docs")
        kwargs.setdefault("docs", Redoc())
        kwargs.setdefault("auth", AuthBear())
        super().__init__(*args, **kwargs)
        self._exception_handlers = get_handlers(self)

    def create_response(
        self,
        request: HttpRequest,
        data: Any,
        *,
        status: int | None = None,
        temporal_response: Any = None,
    ) -> HttpResponse:
        status_code = status or 200
        return super().create_response(
            request,
            {
                "data": data,
                "message_code": "SUCCESS" if 200 <= status_code < 300 else "ERROR",
                "message": "Success" if 200 <= status_code < 300 else "Failed",
                "error_code": 0 if 200 <= status_code < 300 else status_code,
                "current_time": datetime.now(),
            },
            status=status_code,
            temporal_response=temporal_response,
        )
