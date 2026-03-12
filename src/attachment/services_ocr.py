import base64
import logging
import os
import tempfile

from ninja.files import UploadedFile

from attachment.queries import Query as AttachmentQuery
from attachment.schemas.receipt_ocr import OCRReceiptResponse
from utils.services.openai_service import OpenAIService


logger = logging.getLogger(__name__)


class ReceiptOCRService:
    MEDIA_TYPE_MAP = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }

    def __init__(self):
        self.openai_service = OpenAIService()
        self.attachment_query = AttachmentQuery()

    def process_uploaded_file(
        self,
        uploaded_file: UploadedFile,
    ) -> OCRReceiptResponse:
        temp_file_path = None

        try:
            suffix = os.path.splitext(uploaded_file.name)[1] or ".tmp"  # type: ignore
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            return self.process_receipt_file(
                file_path=temp_file_path,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to process uploaded file: {str(e)}") from e

        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    raise

    def process_receipt_file(
        self,
        file_path: str,
    ) -> OCRReceiptResponse:
        try:
            with open(file_path, "rb") as image_file:
                image_data = base64.standard_b64encode(image_file.read()).decode(
                    "utf-8"
                )

            extension = file_path.split(".")[-1].lower()
            media_type = self.MEDIA_TYPE_MAP.get(extension, "image/jpeg")

            parsed_data, tokens_used, model = (
                self.openai_service.extract_receipt_from_image(
                    media_type=media_type,
                    image_data=image_data,
                    target_structure=OCRReceiptResponse,
                )
            )

            logger.info(
                f"Receipt processed successfully using {model} (tokens: {tokens_used})"
            )
            return parsed_data

        except FileNotFoundError as e:
            raise RuntimeError(f"File not found: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to process receipt file: {str(e)}") from e
