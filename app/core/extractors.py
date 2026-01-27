import io
from abc import ABC, abstractmethod

import pypdf
from docx import Document as DocxDocument


class TextExtractor(ABC):
    @abstractmethod
    def can_extract(self, mime_type: str) -> bool:
        pass

    @abstractmethod
    async def extract(self, content: bytes) -> str:
        pass


class PDFExtractor(TextExtractor):
    def can_extract(self, mime_type: str) -> bool:
        return mime_type == "application/pdf"

    async def extract(self, content: bytes) -> str:
        pdf = pypdf.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
        return text


class DOCXExtractor(TextExtractor):
    def can_extract(self, mime_type: str) -> bool:
        return (
            mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    async def extract(self, content: bytes) -> str:
        doc = DocxDocument(io.BytesIO(content))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text


class PlainTextExtractor(TextExtractor):
    def can_extract(self, mime_type: str) -> bool:
        return mime_type in ["text/plain", "text/markdown"]

    async def extract(self, content: bytes) -> str:
        return content.decode("utf-8")


class ExtractionFactory:
    def __init__(self):
        self.extractors = [PDFExtractor(), DOCXExtractor(), PlainTextExtractor()]

    def get_extractor(self, mime_type: str) -> TextExtractor:
        for extractor in self.extractors:
            if extractor.can_extract(mime_type):
                return extractor
        raise ValueError(f"No extractor for mime type: {mime_type}")


extraction_factory = ExtractionFactory()
