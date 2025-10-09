from typing import List
from uuid import UUID

import boto3
from django.conf import settings
from django.db import transaction

from attachment.models import AttachmentType
from authenticate.queries import Query as UserQuery
from exceptions.attachments import AttachmentAlreadyCompleted, AttachmentNotFound
from exceptions.expense import ExpenseNotFound
from exceptions.group import GroupNotFound
from exceptions.message import MessageNotFound
from expense.models import ExpenseAttachment
from expense.queries import Query as ExpenseQuery
from group.queries import Query as GroupQuery
from message.models import MessageAttachment
from message.queries import Query as MessageQuery
from utils.services import BaseService
from utils.types import TUser

from .queries import Query
from .schemas.requests import GeneratePresignedUrlSchema, UidsRequest
from .utils import Utils


class AttachmentService(BaseService):
    def __init__(self) -> None:
        self.query = Query()
        self.utils = Utils()
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
        )
        self.bucket_name = settings.S3_BUCKET_NAME or ""
        self.public_url = (
            settings.S3_PUBLIC_URL.rstrip("/") if settings.S3_PUBLIC_URL else ""
        )
        self.expires_in = settings.S3_EXPIRES_IN

        self.user_query = UserQuery()
        self.group_query = GroupQuery()
        self.expense_query = ExpenseQuery()
        self.message_query = MessageQuery()

    def get_presigned_url(self, user: TUser, payload: GeneratePresignedUrlSchema):
        attachment = self.query.create_new_instance(
            type=payload.attachment_type,
            original_name=payload.file_name,
            hashed_name=self.utils.generate_hashed_name(payload.file_name),
            size=payload.file_size,
            content_type=self.utils.get_content_type(payload.file_name) or "",
            owner=user,
            bucket=self.bucket_name,
        )

        attachment.is_public = True
        attachment.public_url = (
            f"{self.public_url}/{attachment.directory}/{attachment.hashed_name}"
        )
        attachment.save()

        # Generate presigned URL
        presigned_url = self.s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": f"{attachment.directory}/{attachment.hashed_name}",
                "ContentType": attachment.content_type,
            },
            ExpiresIn=self.expires_in,
        )

        return attachment, presigned_url

    @transaction.atomic
    def completed_upload(self, user: TUser, instance_uid: UUID, payload: UidsRequest):
        attachments = self.query.get_instance_by_uids(uids=payload.list_uids)

        if not attachments:
            raise AttachmentNotFound

        for attachment in attachments:
            if attachment.is_completed:
                raise AttachmentAlreadyCompleted

        attachment = attachments[0]
        if attachment.type == AttachmentType.USER:
            if user.avatar_url:
                # TODO: remove old attachment
                self.delete_attachment_s3(public_url=user.avatar_url.public_url)
                self.query.remove_attachments(list_uids=payload.list_uids)

            self.user_query.add_attachment(user=user, attachment=attachment)

        if attachment.type == AttachmentType.GROUP:
            group = self.group_query.get_group_sync(group_uid=instance_uid)

            if not group:
                raise GroupNotFound

            if group.avatar_url:
                # TODO: remove old attachment
                self.delete_attachment_s3(public_url=group.avatar_url.public_url)
                self.query.remove_attachments(list_uids=payload.list_uids)

            self.group_query.add_attachment(group=group, attachment=attachment)

        if attachment.type == AttachmentType.EXPENSE:
            expense = self.expense_query.get_expense(expense_uid=instance_uid)
            if not expense:
                raise ExpenseNotFound

            expense_attachments = []
            for attachment in attachments:
                expense_attachments.append(
                    ExpenseAttachment(expense=expense, attachment=attachment)
                )
            self.expense_query.add_attachment(expense_attachments=expense_attachments)

        if attachment.type == AttachmentType.MESSAGE:
            message = self.message_query.get_message(message_uid=instance_uid)

            if not message:
                raise MessageNotFound

            message_attachments = []
            for attachment in attachments:
                message_attachments.append(
                    MessageAttachment(message=message, attachment=attachment)
                )
            self.message_query.add_attachment(message_attachments=message_attachments)

        self.query.mark_as_completed(attachments=attachments, user=user)

        return True

    @transaction.atomic
    def delete_attachments(self, list_deleted_uids: List[UUID]):
        list_attachments_urls = [
            url[0] for url in self.query.get_public_url_by_uids(uids=list_deleted_uids)
        ]

        if not list_attachments_urls:
            raise AttachmentNotFound
        if len(list_attachments_urls) == 1:
            self.delete_attachment_s3(public_url=list_attachments_urls[0])
        else:
            self.delete_multiple_from_s3(file_keys=list_attachments_urls)

        # TODO: remove attachment => ExpenseAttachment, MessageAttachment will been deleted
        self.query.remove_attachments(list_uids=list_deleted_uids)
        return True

    # ------------- Helper functions -------------
    def delete_attachment_s3(self, public_url: str):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
        )
        key = self.utils.extract_file_key_from_s3_url(public_url)
        s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)

    def delete_multiple_from_s3(self, file_keys: list[str]):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
        )

        objects_to_delete = self.utils.extract_file_key_from_s3_url(file_keys)

        return s3.delete_objects(
            Bucket=settings.S3_BUCKET_NAME,
            Delete={"Objects": objects_to_delete, "Quiet": True},
        )
