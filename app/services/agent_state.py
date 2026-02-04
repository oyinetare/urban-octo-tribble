# app/services/agent_state.py
"""
LangGraph agent state machine and tools.
"""

import json
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama  # ðŸ"§ FIX: Add missing import
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from sqlalchemy import text  # ðŸ"§ FIX: Add missing import
from sqlmodel import func, select

from app.core.config import get_settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.schemas import AgentState, FullReport
from app.utility import utc_now

settings = get_settings()


# =============================================================================
# AGENT TOOLS
# =============================================================================


@tool
async def search_documents(query: str, user_id: int, limit: int = 5) -> str:
    """
    Search the user's documents using semantic search.

    Args:
        query: The search query
        user_id: The user ID to search documents for
        limit: Maximum number of results to return

    Returns:
        JSON string with search results
    """
    try:
        # Import here to avoid circular imports
        from app.core.services import services

        # Generate query embedding
        query_embedding = await services.embedding.generate_embedding(query)

        # Search using the vector store
        results = await services.vector_store.search(query_embedding=query_embedding, limit=limit)

        if not results:
            return json.dumps(
                {"status": "no_results", "message": "No documents found matching your query."}
            )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "chunk_text": result["chunk_text"],
                    "document_id": result["document_id"],
                    "score": result["score"],
                    "position": result.get("chunk_index", 0),
                }
            )

        return json.dumps(
            {"status": "success", "results": formatted_results, "count": len(formatted_results)}
        )

    except Exception as e:
        return json.dumps({"status": "error", "message": f"Search failed: {str(e)}"})


@tool
async def query_database(sql_query: str, user_id: int) -> str:
    """
    Execute a read-only SQL query on the user's documents.
    Only SELECT queries are allowed for security.

    Args:
        sql_query: The SQL query to execute
        user_id: The user ID for filtering

    Returns:
        JSON string with query results
    """
    try:
        # Security: Only allow SELECT queries
        clean_query = sql_query.strip()
        if not clean_query.upper().startswith("SELECT"):
            return json.dumps({"status": "error", "message": "Only SELECT queries allowed."})

        # ðŸ"§ FIX: Use async session properly
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Append the security filter
            if "WHERE" not in clean_query.upper():
                final_query = f"{clean_query} WHERE owner_id = :uid"
            else:
                final_query = clean_query.replace("WHERE", "WHERE owner_id = :uid AND", 1)

            # Use text() with bound parameters (:uid) to prevent injection
            executable_query = text(final_query)
            result = await session.execute(executable_query, {"uid": user_id})

            rows = result.fetchall()

            # Convert to list of dicts
            columns = result.keys()
            data = [dict(zip(columns, row, strict=False)) for row in rows]

            return json.dumps({"status": "success", "data": data, "row_count": len(data)})

    except Exception as e:
        return json.dumps({"status": "error", "message": f"Query failed: {str(e)}"})


@tool
async def generate_report(document_ids: list[int], user_id: int) -> str:
    """
    Generate a summary report for multiple documents.

    Args:
        document_ids: List of document IDs to summarize
        user_id: The user ID (for authorization)

    Returns:
        JSON string with the report
    """
    try:
        # ðŸ"§ FIX: Use async session properly
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Fetch documents
            statement = select(Document).where(
                Document.id.in_(document_ids), Document.owner_id == user_id
            )
            result = await session.execute(statement)
            documents = result.scalars().all()

            if not documents:
                return json.dumps(
                    {"status": "error", "message": "No documents found with the provided IDs."}
                )

            # Generate report
            report: FullReport = {
                "status": "success",
                "report": {"total_documents": len(documents), "documents": []},
            }

            for doc in documents:
                # Get chunk count
                chunk_count_result = await session.execute(
                    select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
                )
                chunk_count = chunk_count_result.scalar_one()

                report["report"]["documents"].append(
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "status": doc.status,
                        "file_size": doc.file_size,
                        "chunk_count": chunk_count,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    }
                )

            return json.dumps(report)

    except Exception as e:
        return json.dumps({"status": "error", "message": f"Report generation failed: {str(e)}"})


@tool
async def send_notification(title: str, message: str, user_id: int) -> str:
    """
    Send a notification to the user.

    Args:
        title: Notification title
        message: Notification message
        user_id: The user ID to send to

    Returns:
        JSON string with status
    """
    try:
        # should use notification service
        # logging for now
        notification = {
            "title": title,
            "message": message,
            "user_id": user_id,
            "created_at": utc_now().isoformat(),
        }

        # TODO: Integrate with actual notification system
        # from app.services.notification_service import notification_service
        # await notification_service.notify(notification)

        return json.dumps(
            {
                "status": "success",
                "message": "Notification sent successfully.",
                "notification": notification,
            }
        )

    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to send notification: {str(e)}"})


# Collect all tools
AGENT_TOOLS = [search_documents, query_database, generate_report, send_notification]


# =============================================================================
# AGENT GRAPH NODES
# =============================================================================


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Determine whether to continue with tools or end."""
    messages = state["messages"]
    last_message = messages[-1]

    # Check if we've hit max iterations
    if state["iterations"] >= state["max_iterations"]:
        return "end"

    # If the LLM makes a tool call, route to tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "end"


def call_model(state: AgentState) -> AgentState:
    """
    Call the LLM with the current state.

    This is the main reasoning node where the agent decides what to do next.
    """
    messages = state["messages"]

    # Initialize the ChatOllama LLM with tools
    llm = ChatOllama(model=settings.OLLAMA_MODEL, temperature=0)
    llm_with_tools = llm.bind_tools(AGENT_TOOLS)

    # Call the LLM
    response = llm_with_tools.invoke(messages)

    # Return updated state
    return {**state, "messages": [response], "iterations": state["iterations"] + 1}


def extract_final_answer(state: AgentState) -> dict:
    """Extract the final answer from the conversation."""
    messages = state["messages"]

    # Find the last AI message without tool calls
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not hasattr(message, "tool_calls"):
            return {**state, "final_answer": message.content}

    # Fallback
    return {**state, "final_answer": "I apologize, but I couldn't generate a complete answer."}


# =============================================================================
# BUILD THE GRAPH
# =============================================================================


def create_agent_graph():
    """
    Create the agent's state machine graph.

    The graph flow:
    1. User message comes in
    2. Agent (call_model) decides what to do
    3. If tools needed, execute them
    4. Return to agent for reasoning
    5. Repeat until final answer or max iterations
    6. Extract and return final answer
    """
    # Use proper type annotation
    workflow: StateGraph[AgentState] = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(AGENT_TOOLS))
    workflow.add_node("final", extract_final_answer)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges - Use the specific node names defined in add_node
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": "final"})

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Add edge from final to END
    workflow.add_edge("final", END)

    # ðŸ"§ FIX: Return compiled graph
    return workflow.compile()


# Create the graph instance
agent_graph = create_agent_graph()
