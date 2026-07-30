"""PDF text extraction with page tracking."""

import io
import asyncio
from typing import Tuple, Dict
import structlog
import pypdf
import pdfplumber

logger = structlog.get_logger()


class PDFService:
    async def extract_text(self, file_bytes: bytes) -> Tuple[str, int, Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._extract_sync, file_bytes)

    def _extract_sync(self, file_bytes: bytes) -> Tuple[str, int, Dict]:
        pages_text = []
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                page_count = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    pages_text.append((page_num, text.strip()))
        except Exception as e:
            logger.warning("pdfplumber failed, using pypdf", error=str(e))
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            page_count = len(reader.pages)
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                pages_text.append((page_num, text.strip()))

        full_text_parts = [f"[PAGE {n}]\n{t}" for n, t in pages_text if t]
        full_text = "\n\n".join(full_text_parts)

        logger.info("PDF extracted", pages=page_count, chars=len(full_text))
        return full_text, page_count, {}

    def build_chunk_page_map(self, full_text: str, chunk_size: int = 1000) -> Dict[int, int]:
        page_map = {}
        lines = full_text.split("\n")
        current_page = 1
        char_count = 0
        chunk_index = 0

        for line in lines:
            if line.startswith("[PAGE "):
                try:
                    current_page = int(line.replace("[PAGE ", "").replace("]", ""))
                except ValueError:
                    pass
                continue
            char_count += len(line) + 1
            if char_count >= chunk_size:
                page_map[chunk_index] = current_page
                chunk_index += 1
                char_count = 0

        page_map[chunk_index] = current_page
        return page_map


pdf_service = PDFService()
