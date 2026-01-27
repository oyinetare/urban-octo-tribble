from datetime import datetime
from typing import Any, cast

import tiktoken
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from app.models import Chunk, Document


class DocumentChunker:
    def __init__(
        self, encoding_name: str = "cl100k_base", chunk_size: int = 500, overlap: int = 50
    ):
        # self.encoder = tiktoken.encoding_for_model(model_name) # "gpt-4"
        self.encoder = tiktoken.get_encoding(encoding_name)
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[tuple[str, int, int]]:
        """Returns a list of (text, position, token_count)"""
        # Edge Case: Empty or whitespace-only documents
        if not text or not text.strip():
            return []

        tokens = self.encoder.encode(text)
        total_tokens = len(tokens)
        chunks = []
        position = 0

        # Handle very short documents (less than chunk size)
        if total_tokens <= self.chunk_size:
            return [(text, 0, total_tokens)]

        start = 0
        while start < total_tokens:
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]

            chunk_text = self.encoder.decode(chunk_tokens)
            chunks.append((chunk_text, position, len(chunk_tokens)))

            position += 1
            # Move start forward by (chunk_size - overlap)
            start += self.chunk_size - self.overlap

            # Prevent infinite loop if overlap >= chunk_size
            if self.overlap >= self.chunk_size:
                break

        return chunks


class ChunkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        self.session.add_all(chunks)
        await self.session.commit()
        return chunks

    async def get_by_document(self, document_id: int) -> list[Chunk]:
        # Cast expressions to Any to bypass "found bool/int" errors in some type checkers
        statement = (
            select(Chunk)
            .where(cast(Any, Chunk.document_id == document_id))
            .order_by(cast(Any, Chunk.position))
        )
        result = await self.session.execute(statement)
        # Convert Sequence to list
        return list(result.scalars().all())

    async def delete_by_document(self, document_id: int):
        statement = delete(Chunk).where(cast(Any, Chunk.document_id == document_id))
        await self.session.execute(statement)
        await self.session.commit()


class ChunkBuilder:
    def __init__(self):
        self._chunks: list[Chunk] = []
        self._document: Document | None = None
        self._chunker: DocumentChunker | None = None

    def from_document(self, document: Document):
        self._document = document
        return self

    def with_chunker(self, chunker: DocumentChunker):
        self._chunker = chunker
        return self

    async def build(self) -> list[Chunk]:
        if not self._document or not self._chunker:
            raise ValueError("Document and Chunker must be provided")

        # Provide a default empty string if content is None to fix Argument type error
        content = self._document.content or ""

        chunks = []
        for chunk_text, position, tokens in self._chunker.chunk(content):
            chunk = Chunk(
                document_id=self._document.id,
                text=chunk_text,
                position=position,
                tokens=tokens,
                created_at=datetime.now(),
            )
            chunks.append(chunk)

        return chunks


chunker = DocumentChunker(chunk_size=500, overlap=50)
