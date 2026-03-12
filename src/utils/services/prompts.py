def build_chat_prompt(media_type: str, image_data: str) -> list[dict]:
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
