from typing import List
from uuid import UUID

from ninja import Schema

from attachment.schemas.requests import GeneratePresignedUrlSchema


class GroupRequest(Schema):
    name: str
    list_user_uids: List[UUID]
    image_file: GeneratePresignedUrlSchema


class GroupUpdateRequest(Schema):
    name: str
    list_user_uids: List[UUID] = []
