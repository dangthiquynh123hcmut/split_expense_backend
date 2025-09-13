from ninja import Schema
from pydantic import Field

from attachment.models import AttachmentType


class GeneratePresignedUrlSchema(Schema):
    file_name: str
    file_size: int = Field(..., description="File size in bytes")
    attachment_type: AttachmentType
