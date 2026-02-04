# app/schemas/agent.py
"""
Schemas for the agent API.
"""

from collections.abc import Sequence
from typing import Annotated, NotRequired

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    The state of the agent conversation.

    Attributes:
        messages: The conversation history, managed via the add_messages reducer.
        iterations: Current count of reasoning loops performed.
        final_answer: The synthesized result to be returned to the user.
        user_id: Unique identifier for the requesting user for scoping data.
        max_iterations: Safety limit to prevent infinite reasoning loops.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    iterations: int
    final_answer: NotRequired[str | None]
    user_id: NotRequired[int]
    max_iterations: NotRequired[int]


class DocEntry(TypedDict):
    """
    Metadata and statistics for an individual document.

    Attributes:
        id: Primary key of the document.
        title: Display name or filename.
        status: Processing status (e.g., 'completed', 'pending').
        file_size: Size of the file in bytes.
        chunk_count: Number of vector chunks associated with this document.
        created_at: ISO-formatted timestamp of creation.
    """

    id: int
    title: str
    status: str
    file_size: int
    chunk_count: int
    created_at: str | None


class ReportData(TypedDict):
    """
    The data payload for a document summary report.

    Attributes:
        total_documents: Count of documents included in the report.
        documents: List of detailed document metadata entries.
    """

    total_documents: int
    documents: list[DocEntry]


class FullReport(TypedDict):
    """
    The top-level JSON structure returned by the report generation tool.

    Attributes:
        status: The outcome of the operation ('success' or 'error').
        report: The nested report data and document list.
    """

    status: str
    report: ReportData


class AgentQueryRequest(BaseModel):
    """Request schema for agent queries."""

    message: str = Field(..., min_length=1, max_length=2000, description="The user's message")
    conversation_history: list[dict] | None = Field(
        None,
        description="Previous messages in the conversation",
        examples=[
            [
                {"role": "user", "content": "What documents do I have?"},
                {"role": "assistant", "content": "You have 5 documents..."},
            ]
        ],
    )
    max_iterations: int | None = Field(
        None,
        ge=1,
        le=20,
        description="Maximum reasoning iterations (default: 10)",
    )


class ToolCall(BaseModel):
    """A tool call made by the agent."""

    tool: str
    args: dict


class ReasoningStep(BaseModel):
    """A reasoning step in the agent's thought process."""

    type: str  # Will be "reasoning" or "tool_execution"
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    timestamp: str


class AgentQueryResponse(BaseModel):
    """Response schema for agent queries."""

    answer: str = Field(..., description="The agent's final answer")
    reasoning_steps: list[ReasoningStep] = Field(..., description="The agent's reasoning process")
    iterations: int = Field(..., description="Number of iterations used")
    tools_used: list[str] = Field(..., description="Tools used by the agent")
    metadata: dict = Field(..., description="Additional metadata")
    conversation_id: int | None = Field(None, description="ID of the saved conversation")


# =============================================================================
# MEMEORY
# =============================================================================


class MemoryCreate(BaseModel):
    """Schema for creating a memory."""

    memory_type: Literal["fact", "preference", "context"]
    key: str = Field(..., min_length=1, max_length=100)
    value: str
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    ttl_days: int | None = Field(None, ge=1, le=365)


class MemoryResponse(BaseModel):
    """Schema for memory response."""

    key: str
    value: str
    importance: float
    last_accessed: str | None


class PreferencesUpdate(BaseModel):
    """Schema for updating preferences."""

    response_style: Literal["concise", "balanced", "detailed"] | None = None
    preferred_language: str | None = None
    tone: Literal["casual", "professional", "technical"] | None = None
    proactive_suggestions: bool | None = None
    web_search_enabled: bool | None = None
    max_iterations: int | None = Field(None, ge=1, le=50)
    notify_on_completion: bool | None = None
    notify_on_insights: bool | None = None


class PreferencesResponse(BaseModel):
    """Schema for preferences response."""

    user_id: int
    response_style: str
    preferred_language: str
    tone: str
    proactive_suggestions: bool
    web_search_enabled: bool
    max_iterations: int
    notify_on_completion: bool
    notify_on_insights: bool
