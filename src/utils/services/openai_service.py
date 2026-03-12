from typing import Any, Optional, Type

from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel


class OpenAIService:
    def __init__(self):
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in Django settings")

        self._client = OpenAI(api_key=api_key)
        self._model = getattr(settings, "OPENAI_MODEL", "gpt-4-turbo")
        self._vision_model = getattr(
            settings, "OPENAI_VISION_MODEL", "gpt-4-vision-preview"
        )
        self._max_tokens = getattr(settings, "OPENAI_MAX_TOKENS", 4096)

    def generate_structured_output(
        self,
        prompt: str,
        target_structure: Type[BaseModel],
        content: str = "",
    ) -> tuple[Any, int, str]:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content},
        ]

        try:
            response = self._client.beta.chat.completions.parse(
                model=self._model, messages=messages, response_format=target_structure
            )
        except Exception as e:
            raise ValueError(f"Failed to connect to OpenAI: {str(e)}") from e

        try:
            return (
                response.choices[0].message.parsed,
                response.usage.total_tokens,
                response.model,
            )
        except Exception as e:
            raise ValueError(f"Failed to parse OpenAI response: {str(e)}") from e

    def read_image_with_vision(
        self, messages: list[dict], max_tokens: Optional[int] = None
    ) -> tuple[str, int, str]:
        try:
            response = self._client.chat.completions.create(
                model=self._vision_model,
                messages=messages,
                max_tokens=max_tokens or self._max_tokens,
            )
        except Exception as e:
            raise ValueError(f"Failed to connect to OpenAI Vision: {str(e)}") from e

        try:
            content = response.choices[0].message.content
            return (content or "", response.usage.total_tokens, response.model)
        except Exception as e:
            raise ValueError(f"Failed to extract image content: {str(e)}") from e

    def extract_receipt_from_image(
        self,
        media_type: str,
        image_data: str,
        target_structure: Type[BaseModel],
    ) -> tuple[Any, int, str]:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}",
                        },
                    },
                    {
                        "type": "text",
                        "text": """You are an expert at extracting structured data from receipts and invoices.

Analyze this receipt image and extract the following information:
- Purchase date
- Total amount
- Currency code (VND, USD, etc.)
- List of items (name, quantity, unit price, total price)
- Suggested expense name (concise and descriptive)
- Suggested expense category (food, transportation, entertainment, shopping, bills, etc.)
- Additional notes if any

Be precise and accurate. If information is not available, mark it as null.""",
                    },
                ],
            }
        ]

        try:
            response = self._client.beta.chat.completions.parse(
                model=self._model,
                messages=messages,
                response_format=target_structure,
            )
        except Exception as e:
            raise ValueError(f"Failed to extract receipt from image: {str(e)}") from e

        try:
            return (
                response.choices[0].message.parsed,
                response.usage.total_tokens,
                response.model,
            )
        except Exception as e:
            raise ValueError(f"Failed to parse receipt data: {str(e)}") from e
