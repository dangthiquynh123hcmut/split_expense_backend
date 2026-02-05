from typing import List
from uuid import UUID

from ninja import File
from ninja.files import UploadedFile

from exceptions.attachments import AttachmentNotFound
from expense.schemas.request import UpdateImageExpense
from utils.router.controller import Controller, api, delete, post, put
from utils.types import AuthenticatedRequest

from .schemas.receipt_ocr import OCRReceiptResponse
from .schemas.requests import GeneratePresignedUrlRequest, UidsRequest
from .schemas.responses import GeneratePresignedUrl
from .services import AttachmentService
from .services_ocr import ReceiptOCRService


@api(prefix_or_class="attachments", tags=["Attachments"])
class AttachmentController(Controller):
    def __init__(
        self, service: AttachmentService, ocr_service: ReceiptOCRService
    ) -> None:
        self.service = service
        self.ocr_service = ocr_service

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
        payload: UidsRequest,
    ):
        return self.service.completed_upload(
            user=request.user, instance_uid=instance_uid, payload=payload
        )

    # TODO: delete attachments
    @delete("", response=bool, exceptions=(AttachmentNotFound,))
    def delete_attachments(self, payload: UidsRequest):
        return self.service.delete_attachments(list_deleted_uids=payload.list_uids)

    @put(
        "/image", response=List[GeneratePresignedUrl], exceptions=(AttachmentNotFound,)
    )
    def update_image_expense(
        self, request: AuthenticatedRequest, payload: UpdateImageExpense
    ):
        if payload.list_deleted_uids:
            self.service.delete_attachments(list_deleted_uids=payload.list_deleted_uids)

        if payload.files:
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

    @post("/ocr/upload", response=OCRReceiptResponse)
    def process_receipt_direct(
        self,
        file: UploadedFile = File(...),
    ) -> OCRReceiptResponse:
        return self.ocr_service.process_uploaded_file(
            uploaded_file=file,
        )
