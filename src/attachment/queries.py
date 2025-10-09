from typing import List
from uuid import UUID

from utils.types import TUser

from .models import Attachment, AttachmentType


class Query:
    def create_new_instance(
        self,
        type: AttachmentType,
        original_name: str,
        hashed_name: str,
        size: float,
        content_type: str,
        owner: TUser,
        bucket: str,
    ):
        return Attachment.objects.create(
            original_name=original_name,
            hashed_name=hashed_name,
            size=size,
            type=type,
            content_type=content_type,
            owner=owner,
            is_public=True,
            bucket=bucket,
        )

    def get_instance_by_uid(self, uid: UUID):
        try:
            return Attachment.objects.get(uid=uid)
        except Attachment.DoesNotExist:
            return None

    @staticmethod
    def get_instance_by_uids(uids: List[UUID]):
        return Attachment.objects.filter(uid__in=uids)

    @staticmethod
    def get_public_url_by_uids(uids: List[UUID]):
        return Attachment.objects.filter(uid__in=uids).values_list("public_url")

    def mark_as_completed(self, attachments: List[Attachment], user: TUser):
        for attachment in attachments:
            attachment.is_completed = True
            attachment.save()
        return attachments

    @staticmethod
    def remove_attachments(list_uids: List[UUID]):
        Attachment.objects.filter(uid__in=list_uids).delete()
