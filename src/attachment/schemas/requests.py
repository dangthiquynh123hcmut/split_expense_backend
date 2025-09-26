from typing import List
from uuid import UUID

from ninja import Schema
from pydantic import Field

from attachment.models import AttachmentType


class GeneratePresignedUrlSchema(Schema):
    file_name: str
    file_size: float = Field(..., description="File size in bytes")
    attachment_type: AttachmentType


class GeneratePresignedUrlRequest(Schema):
    files: List[GeneratePresignedUrlSchema]


class CompletedUploadRequest(Schema):
    list_uids: List[UUID]
