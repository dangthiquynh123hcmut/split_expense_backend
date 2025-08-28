from ninja import ModelSchema

from group.models import Group


class GroupResponse(ModelSchema):
    class Meta:
        model = Group
        exclude = [
            "user_uid",
            "created_at",
            "updated_at",
        ]
