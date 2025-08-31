from ninja import ModelSchema

from group.models import Group


class GroupResponse(ModelSchema):
    class Meta:
        model = Group
        exclude = ["created_at", "updated_at", "status", "name_no_accent"]


# class GroupDetailResponse(GroupResponse):
