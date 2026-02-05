def build_receipt_extraction_prompt() -> str:
    return """You are an expert at extracting structured data from receipts and invoices.

Your task is to analyze the provided receipt/invoice text and extract the following information:
- Purchase date
- Total amount
- Currency
- List of items with their prices
- Appropriate expense name (concise and descriptive)
- Expense category (food, transportation, entertainment, shopping, bills, etc.)


Instructions:
- Be precise and accurate
- If information is not available, mark it as null
- For amounts, use decimal numbers
- Extract all line items with descriptions and prices
- Preserve the original currency information
- Generate a clear, expense name
- Choose the most appropriate category

Return suggestions in structured format following the OCRReceiptResponse schema."""


def build_vision_ocr_prompt() -> str:
    return """Please extract ALL text and content from this receipt/invoice image.

Instructions:
- Extract every single piece of text visible in the image
- Preserve the layout and structure as much as possible
- Include items, prices, totals, dates, and any other information
- For tables or itemized lists, represent them clearly
- Include numbers, currency symbols, and special characters
- For handwritten text, do your best to interpret it
- Maintain the hierarchy of information (headers, items, totals)

Provide the extracted content in plain text format, preserving the original structure as much as possible."""


def build_vision_prompt(media_type: str, image_data: str) -> list[dict]:
    return [
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
                    "text": """Please extract ALL text and content from this image.

Instructions:
- Extract every single piece of text visible in the image
- Preserve the layout and structure as much as possible
- Include numbers, special characters, and formatting
- For tables or forms, represent them in a clear text format
- For handwritten text, do your best to interpret it
- If there are multiple sections, separate them with clear markers

Provide the extracted content in plain text format.""",
                },
            ],
        }
    ]
