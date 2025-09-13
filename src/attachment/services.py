from uuid import UUID

import boto3
from django.conf import settings
from django.core.files import File
from django.db import transaction

from attachment.models import AttachmentType
from authenticate.queries import Query as UserQuery
from exceptions.attachments import AttachmentAlreadyCompleted, AttachmentNotFound
from exceptions.expense import ExpenseNotFound
from exceptions.group import GroupNotFound
from exceptions.message import MessageNotFound
from expense.queries import Query as ExpenseQuery
from group.queries import Query as GroupQuery
from message.queries import Query as MessageQuery
from utils.services import BaseService
from utils.types import TUser

from .queries import Query
from .schemas.requests import GeneratePresignedUrlSchema
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
    def completed_upload(self, user: TUser, uid: UUID, instance_uid: UUID):
        attachment = self.query.get_instance_by_uid(uid=uid)

        if not attachment:
            raise AttachmentNotFound

        if attachment.is_completed:
            raise AttachmentAlreadyCompleted

        if attachment.type == AttachmentType.USER:
            if user.avatar_url:
                # TODO: remove old attachment
                pass

            self.user_query.add_attachment(user=user, attachment=attachment)

        if attachment.type == AttachmentType.GROUP:
            group = self.group_query.get_group_sync(group_uid=instance_uid)

            if not group:
                raise GroupNotFound

            if group.avatar_url:
                # TODO: remove old attachment
                pass

            self.group_query.add_attachment(group=group, attachment=attachment)

        if attachment.type == AttachmentType.EXPENSE:
            expense = self.expense_query.get_expense(expense_uid=instance_uid)

            if not expense:
                raise ExpenseNotFound

            self.expense_query.add_attachment(expense=expense, attachment=attachment)
        if attachment.type == AttachmentType.MESSAGE:
            message = self.message_query.get_message(message_uid=instance_uid)

            if not message:
                raise MessageNotFound

            self.message_query.add_attachment(message=message, attachment=attachment)

        self.query.mark_as_completed(attachment=attachment, user=user)

        return True

    def post_file(self, user: TUser, file: File, type: AttachmentType):
        file_name = file.name or ""
        attachment = self.query.create_new_instance(
            type=type,
            original_name=file_name,
            hashed_name=self.utils.generate_hashed_name(file_name),
            size=file.size,
            content_type=self.utils.get_content_type(file_name) or "",
            owner=user,
            bucket=self.bucket_name,
        )
        attachment.is_public = True
        attachment.public_url = (
            f"{self.public_url}/{attachment.directory}/{attachment.hashed_name}"
        )
        attachment.save()

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=f"{attachment.directory}/{attachment.hashed_name}",
            Body=file,
            ContentType=attachment.content_type,
        )

        return attachment
