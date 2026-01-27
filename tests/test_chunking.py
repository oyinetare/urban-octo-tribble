import pytest

from app.models import Document
from app.services.chunking import ChunkBuilder, DocumentChunker


@pytest.fixture
def chunker():
    return DocumentChunker(chunk_size=10, overlap=2)


def test_chunking_overlap(chunker):
    # 15 tokens will result in 2 chunks: [0:10] and [8:15]
    text = (
        "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen"
    )
    chunks = chunker.chunk(text)

    assert len(chunks) == 2
    # Verify position index
    assert chunks[0][1] == 0
    assert chunks[1][1] == 1
    # Verify overlap (the text 'nine ten' should appear in both)
    assert "nine ten" in chunks[0][0]
    assert "nine ten" in chunks[1][0]


@pytest.mark.asyncio
async def test_chunk_builder_empty_doc(chunker):
    doc = Document(id=1, content="", title="Empty")
    builder = ChunkBuilder().from_document(doc).with_chunker(chunker)

    chunks = await builder.build()
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_chunk_builder_short_doc(chunker):
    doc = Document(id=1, content="Short document.", title="Short")
    builder = ChunkBuilder().from_document(doc).with_chunker(chunker)

    chunks = await builder.build()
    assert len(chunks) == 1
    assert chunks[0].text == "Short document."
    assert chunks[0].tokens > 0


def test_token_count_accuracy(chunker):
    text = "This is a test sentence for token counting."
    chunks = chunker.chunk(text)

    # Calculate tokens using the same encoder
    expected_tokens = len(chunker.encoder.encode(text))
    assert chunks[0][2] == expected_tokens
