from typing import List
from uuid import UUID

from utils.router.controller import Controller, api, post, put
from utils.types import AuthenticatedRequest

from .schemas.requests import CompletedUploadRequest, GeneratePresignedUrlRequest
from .schemas.responses import GeneratePresignedUrl
from .services import AttachmentService


@api(prefix_or_class="attachments", tags=["Attachments"])
class AttachmentController(Controller):
    def __init__(self, service: AttachmentService) -> None:
        self.service = service

    @post("presigned-url", response=List[GeneratePresignedUrl])
    def get_presigned_url(
        self, request: AuthenticatedRequest, payload: GeneratePresignedUrlRequest
    ):
        responses = []
        for file in payload.files:
            attachment, presigned_url = self.service.get_presigned_url(
                user=request.user,
                payload=file,
            )
            responses.append(
                {
                    "uid": attachment.uid,
                    "url": presigned_url,
                    "file_name": file.file_name,
                }
            )

        return responses

    @put("/{instance_uid}/completed", response=bool)
    def completed_upload(
        self,
        request: AuthenticatedRequest,
        instance_uid: UUID,
        payload: CompletedUploadRequest,
    ):
        return self.service.completed_upload(
            user=request.user, instance_uid=instance_uid, payload=payload
        )
