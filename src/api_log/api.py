from ninja import Query

from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, get
from utils.router.paginate import paginate
from utils.router.permissions import IsAdminUser

from .schemas.request import FilterContainer, FilterLogApiSchema
from .schemas.response import LogManagementResponse, LogResponse
from .services import LogService


@api(
    prefix_or_class="/admin/logs",
    tags=["Logs"],
    auth=AuthBear(),
    permissions=[IsAdminUser],
)
class LogAPI(Controller):
    def __init__(self, service: LogService):
        self.service = service

    @get(
        "/",
        response=LogResponse,
        paginate=True,
    )
    @paginate
    def list_logs(
        self,
        filter: FilterLogApiSchema = Query(...),
        filter_container: FilterContainer = Query(...),
    ):
        return self.service.list_logs(filter=filter, filter_container=filter_container)

    @get("/management", response=LogManagementResponse)
    def get_management_log(self):
        return self.service.get_management_log()
