import base64
import logging

from django.conf import settings
from paddleocr import PaddleOCR

from utils.services.openai_service import OpenAIService
from utils.services.prompts import build_vision_prompt


logger = logging.getLogger(__name__)


class FileReader:
    def __init__(self):
        self._ocr_instance = None
        self._pdf_loader = None
        self.openai_service = OpenAIService()

        self.min_text_length = getattr(settings, "OCR_MIN_TEXT_LENGTH", 50)
        self.min_avg_confidence = getattr(settings, "OCR_MIN_AVG_CONFIDENCE", 0.6)

        self.media_type_map = getattr(
            settings,
            "MEDIA_TYPE_MAP",
            {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "gif": "image/gif",
                "webp": "image/webp",
            },
        )

    @property
    def ocr(self):
        if self._ocr_instance is None:
            try:
                self._ocr_instance = PaddleOCR(
                    use_angle_cls=getattr(settings, "PADDLE_OCR_USE_ANGLE_CLS", True),
                    lang=getattr(settings, "PADDLE_OCR_LANG", "vi"),
                )
            except ImportError:
                logger.warning("PaddleOCR not installed")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize PaddleOCR: {str(e)}")
                return None
        return self._ocr_instance

    def detect_ocr_quality(self, confidences: list[float], text_content: str) -> bool:
        if not confidences or not text_content.strip():
            return False

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        text_length = len(text_content.strip())

        return (
            avg_confidence >= self.min_avg_confidence
            and text_length >= self.min_text_length
        )

    def read_image_with_paddleocr(self, file_path: str) -> tuple[str, bool]:
        if self.ocr is None:
            return "", False

        try:
            ocr_result = self.ocr.ocr(file_path, cls=True)
            text_lines = []
            confidences = []

            for page in ocr_result:
                if page:
                    for word_info in page:
                        try:
                            if not hasattr(word_info, "__len__") or len(word_info) < 2:
                                continue

                            text_item = word_info[1]
                            text = (
                                str(text_item)
                                if not isinstance(text_item, str)
                                else text_item
                            )

                            if text.strip():
                                text_lines.append(text)

                                if len(word_info) >= 3:
                                    try:
                                        confidence = float(word_info[2])
                                        confidences.append(confidence)
                                    except (ValueError, TypeError):
                                        confidences.append(0.9)
                                else:
                                    confidences.append(0.9)

                        except (IndexError, TypeError, AttributeError):
                            continue

            return "\n".join(text_lines), self.detect_ocr_quality(
                confidences, "\n".join(text_lines)
            )

        except Exception:
            return "", False

    def read_image_with_vision(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as image_file:
                image_data = base64.standard_b64encode(image_file.read()).decode(
                    "utf-8"
                )

            extension = file_path.split(".")[-1].lower()
            media_type = self.media_type_map.get(extension, "image/jpeg")

            messages = build_vision_prompt(media_type=media_type, image_data=image_data)
            content, _, _ = self.openai_service.read_image_with_vision(
                messages=messages
            )

            return content

        except Exception as e:
            raise e

    def read_image(self, file_path: str) -> str:
        paddle_text, is_high_quality = self.read_image_with_paddleocr(file_path)

        if not is_high_quality:
            try:
                return self.read_image_with_vision(file_path)
            except Exception:
                return paddle_text if paddle_text else ""

        return paddle_text

    def read(self, file_path: str) -> str:
        file_path_lower = file_path.lower()

        if file_path_lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            return self.read_image(file_path)
        else:
            raise ValueError("Unsupported file type for OCR")
