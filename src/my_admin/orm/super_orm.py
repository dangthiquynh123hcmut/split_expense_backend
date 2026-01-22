from django.db import IntegrityError

from authenticate.models import User
from exceptions.users import EmailAlreadyExists
from my_admin.schemas.request import AdminCreateRequest, FilterAdminSchema


class SuperORM:
    @staticmethod
    def create_admin(data: AdminCreateRequest):
        try:
            return User.objects.create_admin(email=data.email, role="ADMIN")
        except IntegrityError:
            raise EmailAlreadyExists

    @staticmethod
    def list_admins(filter: FilterAdminSchema):
        return User.objects.filter(filter.get_filter_expression(), role="ADMIN")

    @staticmethod
    def activate_user(user: User, password: str):
        user.password = password
        user.save()
