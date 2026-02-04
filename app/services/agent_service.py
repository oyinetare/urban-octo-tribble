# app/services/agent_service.py
"""
Agent service for managing conversations and agent interactions.
"""

from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage

from app.core.database import AsyncSessionLocal
from app.models.query import Query
from app.services.agent_state import AgentState, agent_graph
from app.utility import utc_now


class AgentService:
    """
    Service for interacting with the LangGraph agent.
    """

    def __init__(self, max_iterations: int = 10):
        self.max_iterations = max_iterations
        self.graph = agent_graph

    async def query(
        self, message: str, user_id: int, conversation_history: list[dict] | None = None
    ) -> dict:
        """
        Send a query to the agent and get a response.

        Args:
            message: The user's message
            user_id: The user ID
            conversation_history: Previous messages in the conversation

        Returns:
            Dict with the agent's response and metadata
        """
        # Build messages list
        messages = []

        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        # Add current message
        messages.append(HumanMessage(content=message))

        # Create initial state
        initial_state: AgentState = {
            "messages": messages,
            "iterations": 0,
            "final_answer": None,
            "user_id": user_id,
            "max_iterations": self.max_iterations,
        }

        # Run the agent
        result = self.graph.invoke(initial_state)

        # Extract reasoning steps
        reasoning_steps = []
        for msg in result["messages"]:
            if isinstance(msg, AIMessage):
                step = {
                    "type": "reasoning",
                    "content": msg.content,
                    "timestamp": utc_now().isoformat(),  # FIX: Use timezone-aware datetime
                }

                # Add tool calls if present
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    step["tool_calls"] = [
                        {"tool": call["name"], "args": call["args"]} for call in msg.tool_calls
                    ]

                reasoning_steps.append(step)

        return {
            "answer": result["final_answer"],
            "reasoning_steps": reasoning_steps,
            "iterations": result["iterations"],
            "tools_used": self._extract_tools_used(result["messages"]),
            "metadata": {
                "user_id": user_id,
                "max_iterations_reached": result["iterations"] >= self.max_iterations,
                "timestamp": utc_now().isoformat(),  # Use timezone-aware datetime
            },
        }

    async def stream_query(
        self, message: str, user_id: int, conversation_history: list[dict] | None = None
    ) -> AsyncIterator[dict]:
        """
        Stream the agent's reasoning process in real-time.

        Yields:
            Dict events as the agent processes the query
        """
        # Build messages
        messages = []
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=message))

        # Create initial state
        initial_state: AgentState = {
            "messages": messages,
            "iterations": 0,
            "final_answer": None,
            "user_id": user_id,
            "max_iterations": self.max_iterations,
        }

        # Stream events
        async for event in self.graph.astream(initial_state):
            # Determine event type
            if "agent" in event:
                # Agent thinking
                agent_state = event["agent"]
                last_message = agent_state["messages"][-1]

                yield {
                    "type": "thinking",
                    "iteration": agent_state["iterations"],
                    "content": last_message.content if hasattr(last_message, "content") else "",
                    "tool_calls": (
                        [
                            {"tool": call["name"], "args": call["args"]}
                            for call in last_message.tool_calls
                        ]
                        if hasattr(last_message, "tool_calls") and last_message.tool_calls
                        else []
                    ),
                }

            elif "tools" in event:
                # Tool execution
                tools_state = event["tools"]

                yield {
                    "type": "tool_execution",
                    "tools": self._extract_tool_results(tools_state["messages"]),
                }

            elif "final" in event:
                # Final answer
                final_state = event["final"]

                yield {
                    "type": "answer",
                    "content": final_state["final_answer"],
                    "iterations": final_state["iterations"],
                }

    def _extract_tools_used(self, messages: list) -> list[str]:
        """Extract unique tool names used during the conversation."""
        tools = set()

        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for call in msg.tool_calls:
                    tools.add(call["name"])

        return list(tools)

    def _extract_tool_results(self, messages: list) -> list[dict]:
        """Extract tool execution results from messages."""
        results = []

        for msg in messages:
            if hasattr(msg, "name"):  # ToolMessage
                results.append({"tool": msg.name, "result": msg.content})

        return results

    async def save_conversation(
        self,
        user_id: int,
        query: str,
        answer: str,
        reasoning_steps: list[dict],
        tools_used: list[str],
    ) -> Query:
        """
        Save the agent conversation to the database.

        Returns:
            The created Query object
        """
        # ðŸ"§ FIX: Use async session properly
        async with AsyncSessionLocal() as session:
            query_record = Query(
                user_id=user_id,
                query=query,
                answer=answer,
                chunks_used=[],  # Agent doesn't use chunks directly
                complexity="complex",  # Agent queries are complex by definition
                metadata={
                    "reasoning_steps": reasoning_steps,
                    "tools_used": tools_used,
                    "agent_type": "langgraph",
                },
            )

            session.add(query_record)
            await session.commit()
            await session.refresh(query_record)

            return query_record


# Create singleton instance
agent_service = AgentService(max_iterations=10)
