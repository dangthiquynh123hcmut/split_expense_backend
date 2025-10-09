import hashlib
import mimetypes
import os
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse


class Utils:
    @staticmethod
    def generate_hashed_name(file_name: str) -> str:
        name, extension = os.path.splitext(file_name)
        timestamp = datetime.now().timestamp()
        hashed_name = hashlib.sha256(f"{name}{timestamp}".encode()).hexdigest()
        return f"{hashed_name}{extension}"

    @staticmethod
    def get_content_type(file_name: str) -> Optional[str]:
        mime, _ = mimetypes.guess_type(file_name)
        return mime

    @staticmethod
    def extract_file_key_from_s3_url(url_or_urls):
        def extract_one(url: str) -> str:
            parsed = urlparse(url)
            return parsed.path.lstrip("/")

        if isinstance(url_or_urls, (list, tuple, set)):
            return [{"Key": extract_one(u)} for u in url_or_urls if u]
        elif isinstance(url_or_urls, str):
            return extract_one(url_or_urls)
