import datetime

from django.db.models import Avg
from django.utils.timezone import now

from utils.functions.get_last_month import get_last_month

from .models import ApiLog
from .schemas.request import CreateLogSchema, FilterContainer, FilterLogApiSchema


class Query:
    @staticmethod
    def create_log(log_data: CreateLogSchema):
        return ApiLog.objects.create(**log_data.dict())

    @staticmethod
    def list_logs(filter: FilterLogApiSchema, filter_container: FilterContainer):
        query = ApiLog.objects.all()
        if filter_container and filter_container.search:
            query = query.filter(filter_container.get_filter_expression())
        if filter and filter.method_type:
            query = query.filter(method_type__icontains=filter.method_type)
        if filter and filter.status_code:
            if filter.status_code == "2xx":
                query = query.filter(status_code__gte=200, status_code__lt=300)
            elif filter.status_code == "4xx":
                query = query.filter(status_code__gte=400, status_code__lt=500)
            elif filter.status_code == "5xx":
                query = query.filter(status_code__gte=500, status_code__lt=600)
        return query

    @staticmethod
    def get_total_errors():
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return ApiLog.objects.filter(
            status_code__gte=400, created_at__gte=start_this_month
        ).count(), ApiLog.objects.filter(
            status_code__gte=400,
            created_at__gte=start_last_month,
            created_at__lt=start_this_month,
        ).count()

    @staticmethod
    def get_today_errors():
        today = now().date()
        yesterday = today - datetime.timedelta(days=1)
        return ApiLog.objects.filter(
            status_code__gte=400, created_at__date=today
        ).count(), ApiLog.objects.filter(
            status_code__gte=400, created_at__date=yesterday
        ).count()

    @staticmethod
    def get_avg_response_time():
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        avg_response_time_this_month = (
            ApiLog.objects.filter(created_at__gte=start_this_month).aggregate(
                avg_response_time=Avg("response_time")
            )
        )["avg_response_time"]

        avg_response_time_last_month = (
            ApiLog.objects.filter(
                created_at__gte=start_last_month, created_at__lt=start_this_month
            ).aggregate(avg_response_time=Avg("response_time"))
        )["avg_response_time"]
        return avg_response_time_this_month, avg_response_time_last_month
