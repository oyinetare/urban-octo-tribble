"""
API routes for the LangGraph agent.
"""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import get_current_user
from app.exceptions import AppException
from app.models.query import Query
from app.models.user import User
from app.schemas.agent import AgentQueryRequest, AgentQueryResponse
from app.services.agent_service import agent_service

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(request: AgentQueryRequest, current_user: User = Depends(get_current_user)):
    """
    Send a query to the AI agent.

    The agent will:
    1. Analyze your question
    2. Decide which tools to use
    3. Execute tools (search documents, query database, etc.)
    4. Reason about the results
    5. Provide a comprehensive answer

    Example queries:
    - "What are my most recent documents about AI?"
    - "Search for documents mentioning 'machine learning' and summarize them"
    - "How many documents did I upload this month?"
    """
    try:
        # Override max_iterations if provided
        if request.max_iterations:
            agent_service.max_iterations = request.max_iterations

        # Query the agent
        result = await agent_service.query(
            message=request.message,
            user_id=current_user.id,
            conversation_history=request.conversation_history,
        )

        # Save conversation
        conversation = await agent_service.save_conversation(
            user_id=current_user.id,
            query=request.message,
            answer=result["answer"],
            reasoning_steps=result["reasoning_steps"],
            tools_used=result["tools_used"],
        )

        return AgentQueryResponse(
            answer=result["answer"],
            reasoning_steps=result["reasoning_steps"],
            iterations=result["iterations"],
            tools_used=result["tools_used"],
            metadata=result["metadata"],
            conversation_id=conversation.id,
        )

    except Exception as e:
        raise AppException(status_code=500, message=f"Agent query failed: {str(e)}") from e


@router.post("/query/stream")
async def stream_agent_query(
    request: AgentQueryRequest, current_user: User = Depends(get_current_user)
):
    """
    Stream the agent's reasoning process in real-time.

    This endpoint uses Server-Sent Events (SSE) to stream the agent's
    thinking process, tool executions, and final answer.

    Event types:
    - `thinking`: Agent is reasoning about what to do
    - `tool_execution`: Agent is executing a tool
    - `answer`: Final answer (last event)
    """

    async def event_generator():
        """Generate SSE events."""
        try:
            # Override max_iterations if provided
            if request.max_iterations:
                agent_service.max_iterations = request.max_iterations

            # Track for saving later
            all_steps = []
            tools_used = set()
            final_answer = None

            # Stream events
            async for event in agent_service.stream_query(
                message=request.message,
                user_id=current_user.id,
                conversation_history=request.conversation_history,
            ):
                # Track data
                if event["type"] == "thinking":
                    all_steps.append(event)
                    if event.get("tool_calls"):
                        for call in event["tool_calls"]:
                            tools_used.add(call["tool"])

                elif event["type"] == "tool_execution":
                    all_steps.append(event)

                elif event["type"] == "answer":
                    final_answer = event["content"]

                # Send SSE event
                yield f"data: {json.dumps(event)}\n\n"

            # Save conversation
            if final_answer:
                await agent_service.save_conversation(
                    user_id=current_user.id,
                    query=request.message,
                    answer=final_answer,
                    reasoning_steps=all_steps,
                    tools_used=list(tools_used),
                )

            # Send completion event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),  # ðŸ"§ FIX: Use async session
):
    """
    List the user's agent conversations.

    Returns conversations sorted by most recent first.
    """
    statement = (
        select(Query)
        .where(Query.user_id == current_user.id)
        # 1. Cast or ensure the type checker knows this is a JSON column for subscripting
        .where(Query.metadata["agent_type"].astext == "langgraph")
        # 2. Use the desc() function explicitly
        .order_by(desc(Query.created_at))
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(statement)
    conversations = result.scalars().all()

    return {
        "conversations": [
            {
                "id": conv.id,
                "query": conv.query,
                "answer": conv.answer[:200] + "..." if len(conv.answer) > 200 else conv.answer,
                "tools_used": conv.metadata.get("tools_used", []) if conv.metadata else [],
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
            }
            for conv in conversations
        ],
        "total": len(conversations),
        "limit": limit,
        "offset": offset,
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),  # ðŸ"§ FIX: Use async session
):
    """
    Get a specific agent conversation with full details.
    """
    # ðŸ"§ FIX: Use async session properly
    conversation = await session.get(Query, conversation_id)

    if not conversation:
        raise AppException(status_code=404, message="Conversation not found")

    # Check ownership
    if conversation.user_id != current_user.id:
        raise AppException(status_code=403, message="Access denied")

    return {
        "id": conversation.id,
        "query": conversation.query,
        "answer": conversation.answer,
        "reasoning_steps": conversation.metadata.get("reasoning_steps", [])
        if conversation.metadata
        else [],
        "tools_used": conversation.metadata.get("tools_used", []) if conversation.metadata else [],
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
    }
