from typing import List
from uuid import UUID

from ninja import Schema


class GeneratePresignedUrl(Schema):
    uid: UUID
    url: str
    file_name: str


class GeneratePresignedUrlResponse(Schema):
    files: List[GeneratePresignedUrl]


class AttachmentResponse(Schema):
    uid: UUID
    original_name: str
    public_url: str
