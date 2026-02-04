"""
Event schemas for the event streaming system.

All events follow a common structure:
- event_type: Type of event (e.g., "document.uploaded")
- event_id: Unique event ID (Snowflake)
- timestamp: When event occurred (ISO 8601)
- user_id: User who triggered the event
- data: Event-specific payload
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class EventType(str, Enum):
    """Event types for the system."""

    # Document lifecycle events
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSING_STARTED = "document.processing_started"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_CHUNKED = "document.chunked"
    DOCUMENT_EMBEDDED = "document.embedded"
    DOCUMENT_COMPLETED = "document.completed"
    DOCUMENT_FAILED = "document.failed"
    DOCUMENT_DELETED = "document.deleted"

    # Query events
    QUERY_EXECUTED = "query.executed"
    QUERY_CACHED = "query.cached"
    QUERY_FAILED = "query.failed"

    # User events
    USER_REGISTERED = "user.registered"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"


class BaseEvent(BaseModel):
    """Base event structure for all events."""

    event_type: EventType
    event_id: int  # Snowflake ID
    timestamp: datetime
    user_id: int | None = None  # Some events might not have user context

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# DOCUMENT EVENTS
# ============================================================================


class DocumentUploadedData(BaseModel):
    """Data payload for document.uploaded event."""

    document_id: int
    title: str
    filename: str
    file_size: int
    content_type: str


class DocumentUploadedEvent(BaseEvent):
    """Event: User uploaded a document."""

    event_type: EventType = EventType.DOCUMENT_UPLOADED
    data: DocumentUploadedData


class DocumentProcessingStartedData(BaseModel):
    """Data payload for document.processing_started event."""

    document_id: int
    task_id: str


class DocumentProcessingStartedEvent(BaseEvent):
    """Event: Document processing started in Celery."""

    event_type: EventType = EventType.DOCUMENT_PROCESSING_STARTED
    data: DocumentProcessingStartedData


class DocumentProcessedData(BaseModel):
    """Data payload for document.processed event."""

    document_id: int
    text_length: int
    extraction_time_ms: int


class DocumentProcessedEvent(BaseEvent):
    """Event: Text extracted from document."""

    event_type: EventType = EventType.DOCUMENT_PROCESSED
    data: DocumentProcessedData


class DocumentChunkedData(BaseModel):
    """Data payload for document.chunked event."""

    document_id: int
    chunks_count: int
    avg_chunk_size: int


class DocumentChunkedEvent(BaseEvent):
    """Event: Document split into chunks."""

    event_type: EventType = EventType.DOCUMENT_CHUNKED
    data: DocumentChunkedData


class DocumentEmbeddedData(BaseModel):
    """Data payload for document.embedded event."""

    document_id: int
    embeddings_count: int
    embedding_time_ms: int


class DocumentEmbeddedEvent(BaseEvent):
    """Event: Embeddings generated for document."""

    event_type: EventType = EventType.DOCUMENT_EMBEDDED
    data: DocumentEmbeddedData


class DocumentCompletedData(BaseModel):
    """Data payload for document.completed event."""

    document_id: int
    total_processing_time_ms: int


class DocumentCompletedEvent(BaseEvent):
    """Event: Document fully processed and ready."""

    event_type: EventType = EventType.DOCUMENT_COMPLETED
    data: DocumentCompletedData


class DocumentFailedData(BaseModel):
    """Data payload for document.failed event."""

    document_id: int
    error_message: str
    failed_stage: str  # "extraction", "chunking", "embedding"


class DocumentFailedEvent(BaseEvent):
    """Event: Document processing failed."""

    event_type: EventType = EventType.DOCUMENT_FAILED
    data: DocumentFailedData


class DocumentDeletedData(BaseModel):
    """Data payload for document.deleted event."""

    document_id: int
    title: str


class DocumentDeletedEvent(BaseEvent):
    """Event: Document deleted by user."""

    event_type: EventType = EventType.DOCUMENT_DELETED
    data: DocumentDeletedData


# ============================================================================
# QUERY EVENTS
# ============================================================================


class QueryExecutedData(BaseModel):
    """Data payload for query.executed event."""

    query_id: int
    document_id: int | None
    query_text: str
    answer_length: int
    chunks_used: int
    llm_provider: str
    llm_model: str
    tokens_used: int | None
    response_time_ms: int
    cache_hit: bool = False


class QueryExecutedEvent(BaseEvent):
    """Event: RAG query executed."""

    event_type: EventType = EventType.QUERY_EXECUTED
    data: QueryExecutedData


class QueryCachedData(BaseModel):
    """Data payload for query.cached event."""

    query_text: str
    document_id: int | None
    response_time_ms: int


class QueryCachedEvent(BaseEvent):
    """Event: Query served from cache."""

    event_type: EventType = EventType.QUERY_CACHED
    data: QueryCachedData


class QueryFailedData(BaseModel):
    """Data payload for query.failed event."""

    query_text: str
    error_message: str


class QueryFailedEvent(BaseEvent):
    """Event: Query execution failed."""

    event_type: EventType = EventType.QUERY_FAILED
    data: QueryFailedData


# ============================================================================
# USER EVENTS
# ============================================================================


class UserRegisteredData(BaseModel):
    """Data payload for user.registered event."""

    username: str
    email: str
    tier: str
    role: str


class UserRegisteredEvent(BaseEvent):
    """Event: New user registered."""

    event_type: EventType = EventType.USER_REGISTERED
    data: UserRegisteredData


class UserLoginData(BaseModel):
    """Data payload for user.login event."""

    username: str
    tier: str


class UserLoginEvent(BaseEvent):
    """Event: User logged in."""

    event_type: EventType = EventType.USER_LOGIN
    data: UserLoginData


class UserLogoutData(BaseModel):
    """Data payload for user.logout event."""

    username: str


class UserLogoutEvent(BaseEvent):
    """Event: User logged out."""

    event_type: EventType = EventType.USER_LOGOUT
    data: UserLogoutData
