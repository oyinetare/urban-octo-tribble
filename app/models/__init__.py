from app.models.chunk import Chunk
from app.models.document import Document
from app.models.query import Query
from app.models.shorturl import ShortURL
from app.models.user import User

# model_rebuild() calls at the bottom
# This tells Pydantic (running under Python 3.13) to go back and
# connect the dots between Document and Chunk once all files are loaded.
# User.model_rebuild()
# ShortURL.model_rebuild()
# Query.model_rebuild()
# Document.model_rebuild()
# Chunk.model_rebuild()

__all__ = ["Chunk", "Document", "Query", "ShortURL", "User"]
