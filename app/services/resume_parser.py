from __future__ import annotations

import logging
from pathlib import Path

from docx import Document
from pdfminer.high_level import extract_text

from app.core.exceptions import ResumeParseError


logger = logging.getLogger(__name__)


class ResumeParserService:
    def parse_pdf(self, path: Path) -> str:
        logger.info("Parsing PDF file=%s", path)
        try:
            return extract_text(str(path)).strip()
        except Exception as exc:
            raise ResumeParseError("Failed to parse PDF file", {"path": str(path)}) from exc

    def parse_docx(self, path: Path) -> str:
        logger.info("Parsing DOCX file=%s", path)
        try:
            document = Document(str(path))
            return "\n".join(p.text for p in document.paragraphs).strip()
        except Exception as exc:
            raise ResumeParseError("Failed to parse DOCX file", {"path": str(path)}) from exc

    def parse_resume(self, path: Path) -> str:
        extension = path.suffix.lower()
        if extension == ".pdf":
            text = self.parse_pdf(path)
        elif extension == ".docx":
            text = self.parse_docx(path)
        else:
            raise ResumeParseError("Unsupported resume format", {"path": str(path), "extension": extension})

        if not text.strip():
            raise ResumeParseError("Resume text is empty after parsing", {"path": str(path)})
        return text
