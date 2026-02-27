from api_log.schemas.response import LogManagementResponse

from .queries import Query
from .schemas.request import FilterContainer, FilterLogApiSchema


class LogService:
    def __init__(self):
        self.query = Query()

    def list_logs(self, filter: FilterLogApiSchema, filter_container: FilterContainer):
        return self.query.list_logs(filter=filter, filter_container=filter_container)

    def get_management_log(self):
        total_errors, total_errors_last_month = self.query.get_total_errors()
        today_errors, yesterday_errors = self.query.get_today_errors()
        avg_response_time_this_month, avg_response_time_last_month = (
            self.query.get_avg_response_time()
        )
        total_errors = total_errors or 0
        total_errors_last_month = total_errors_last_month or 0
        today_errors = today_errors or 0
        yesterday_errors = yesterday_errors or 0
        avg_response_time_last_month = avg_response_time_last_month or 0
        avg_response_time_this_month = avg_response_time_this_month or 0

        return LogManagementResponse(
            total_errors=total_errors,
            percent_increase_errors=(
                (total_errors - total_errors_last_month) / total_errors_last_month * 100
            )
            if total_errors_last_month
            else 100.0,
            today_errors=today_errors,
            percent_increase_today_errors=(
                (today_errors - yesterday_errors) / yesterday_errors * 100
            )
            if yesterday_errors
            else 100.0,
            avg_response_time=avg_response_time_this_month,
            percent_increase_avg_response_time=(
                (avg_response_time_this_month - avg_response_time_last_month)
                / avg_response_time_last_month
                * 100
            )
            if avg_response_time_last_month
            else 100.0,
        )
