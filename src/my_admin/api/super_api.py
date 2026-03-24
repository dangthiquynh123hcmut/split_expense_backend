from uuid import UUID

from ninja import Query

from exceptions.users import EmailAlreadyExists
from my_admin.schemas.request import (
    ActiveAdminRequest,
    AdminCreateRequest,
    FilterAdminSchema,
)
from my_admin.schemas.response import AdminResponse
from my_admin.service.super_service import SuperService
from utils.router.controller import Controller, api, delete, get, patch, post
from utils.router.paginate import paginate
from utils.router.permissions import IsSuperUser


@api(
    prefix_or_class="admin",
    tags=["Admin"],
    auth=None,
    permissions=[IsSuperUser],
)
class SuperController(Controller):
    def __init__(self, service: SuperService):
        self.service = service

    @post("", auth=True, response=bool, exceptions=(EmailAlreadyExists,))
    def create_admin(self, data: AdminCreateRequest):
        return self.service.create_admin(data=data)

    @get("", auth=True, response=AdminResponse, paginate=True)
    @paginate
    def list_admins(self, filter: FilterAdminSchema = Query(...)):
        return self.service.list_admins(filter=filter)

    @delete("/{admin_uid}", auth=True, response=bool)
    def delete_admin(self, admin_uid: UUID):
        self.service.delete_admin(admin_uid=admin_uid)
        return True

    @patch("/{admin_uid}/deactivate", auth=True, response=bool)
    def deactivate_admin(self, admin_uid: UUID):
        self.service.deactivate_admin(admin_uid=admin_uid)
        return True


@api(
    prefix_or_class="admins",
    tags=["Admin"],
    auth=None,
)
class ActivateAdminController(Controller):
    def __init__(self, service: SuperService):
        self.service = service

    @patch("/activate", response=bool)
    def activate_admin(self, body: ActiveAdminRequest):
        self.service.activate_admin(body=body)
        return True
