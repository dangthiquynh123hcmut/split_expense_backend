import logging
import os
import tempfile

from ninja.files import UploadedFile

from attachment.queries import Query as AttachmentQuery
from attachment.schemas.receipt_ocr import OCRReceiptResponse
from utils.services.file_reader import FileReader
from utils.services.openai_service import OpenAIService
from utils.services.prompts import build_receipt_extraction_prompt


logger = logging.getLogger(__name__)


class ReceiptOCRService:
    def __init__(self):
        self.file_reader = FileReader()
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
        extracted_text = self.file_reader.read(file_path)

        if not extracted_text:
            raise ValueError("No text extracted from the file")

        try:
            return self._extract_receipt_data(extracted_text)
        except Exception as e:
            raise RuntimeError(f"Structured data extraction failed: {str(e)}") from e

    def _extract_receipt_data(self, text_content: str) -> OCRReceiptResponse:
        prompt = build_receipt_extraction_prompt()

        parsed_data, _, _ = self.openai_service.generate_structured_output(
            prompt=prompt,
            target_structure=OCRReceiptResponse,
            content=text_content,
        )

        return parsed_data
