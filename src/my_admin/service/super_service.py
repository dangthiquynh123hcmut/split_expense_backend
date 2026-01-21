from uuid import UUID

from django.core.cache import cache

from authenticate.models import generate_token
from authenticate.queries import Query as AuthQuery
from exceptions.users import AdminCreateFail, UserNotFound
from my_admin.schemas.request import AdminCreateRequest, FilterAdminSchema
from split_expense_system import settings
from utils.services.base import BaseService
from utils.services.email.client import EmailClient
from utils.services.email.template import EmailTemplate

from ..orm.super_orm import SuperORM


class SuperService(BaseService):
    def __init__(self):
        self.super_orm = SuperORM()
        self.email_template = EmailTemplate()
        self.email_client = EmailClient()
        self.auth_query = AuthQuery()
        self._time_out = settings.REDIS_TOKEN_TTL_ADMIN_ACTIVATE_ACCOUNT

    def create_admin(self, data: AdminCreateRequest):
        user = self.super_orm.create_admin(data=data)
        if not user:
            raise AdminCreateFail

        token = generate_token()

        token_key = f"admin_activate_token:{token}"
        cache.set(token_key, user.uid, timeout=self._time_out)

        self.logger.info(f"Token saved to Redis for admin {user.uid}")

        template = self.email_template.account_active(user=user, token=token)
        self.email_client.send(messages=[template])
        return True

    def list_admins(self, filter: FilterAdminSchema):
        list_admins = self.super_orm.list_admins(filter=filter)
        for admin in list_admins:
            if not admin.last_login:
                setattr(admin, "status", "INACTIVE")
            else:
                setattr(admin, "status", "INACTIVE")
        return list_admins

    def delete_admin(self, admin_uid: UUID):
        admin = self.auth_query.get_user_by_uid(uid=admin_uid)
        if not admin or not admin.is_staff:
            raise UserNotFound
        self.auth_query.delete_user(user=admin)
