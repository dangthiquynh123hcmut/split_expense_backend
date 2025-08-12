from uuid import UUID

import boto3
from django.conf import settings
from django.core.files import File
from django.db import transaction

from attachment.models import AttachmentType
from dish.orm import DishORM
from exceptions.attachments import AttachmentAlreadyCompleted, AttachmentNotFound
from exceptions.dishes import DishNotFoundException
from exceptions.food import FoodDoesNotExist
from food.orm import FoodORM
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

        self.food_orm = FoodORM()
        self.dish_orm = DishORM()

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

        if attachment.type == AttachmentType.FOOD:
            food = self.food_orm.get_food_by_uid(uid=instance_uid)

            if not food:
                raise FoodDoesNotExist

            if food.attachment:
                # TODO: remove old attachment
                pass

            self.food_orm.add_attachment(food=food, attachment=attachment)

        if attachment.type == AttachmentType.DISH:
            dish = self.dish_orm.get_dish_by_uid(uid=instance_uid)

            if not dish:
                raise DishNotFoundException

            if dish.attachment:
                # TODO: remove old attachment
                pass

            self.dish_orm.add_attachment(dish=dish, attachment=attachment)

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
