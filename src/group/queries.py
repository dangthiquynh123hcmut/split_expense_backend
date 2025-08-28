from authenticate.models import User

from .models import Group


class Query:
    @staticmethod
    def create_group(leader: User, name: str) -> Group:
        return Group.objects.create(leader=leader, name=name)
