# app/services/enhanced_agent_state.py
"""
Enhanced agent state with improved prompts, memory integration, and all tools.
"""

from collections.abc import Sequence
from typing import Annotated, Literal, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.services.agent_memory import memory_service
from app.services.agent_state import (
    generate_report,
    query_database,
    search_documents,
    send_notification,
)
from app.services.agent_tools import ENHANCED_TOOLS

# =============================================================================
# AGENT STATE WITH MEMORY
# =============================================================================


class EnhancedAgentState(TypedDict):
    """
    Enhanced agent state with memory and context.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    iterations: int
    final_answer: str | None
    user_id: int
    max_iterations: int
    user_context: str  # Built from memory
    conversation_id: int | None


# =============================================================================
# COMBINE ALL TOOLS
# =============================================================================

ALL_AGENT_TOOLS = [
    # Original tools
    search_documents,
    query_database,
    generate_report,
    send_notification,
    # Enhanced tools
    *ENHANCED_TOOLS,
]


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

AGENT_SYSTEM_PROMPT = """You are an intelligent document analysis assistant with access to multiple tools.

# Your Capabilities

You can help users:
- **Search and analyze documents**: Use semantic search to find relevant information
- **Compare documents**: Analyze similarities and differences between multiple documents
- **Generate reports**: Create comprehensive summaries and analyses
- **Perform statistical analysis**: Provide insights about document collections and usage patterns
- **Search the web**: Find current information when needed
- **Execute database queries**: Answer questions requiring structured data queries

# Guidelines

## When to use each tool:

**search_documents**:
- User asks about content IN their documents
- Need to find specific information from uploaded files
- Example: "What do my documents say about AI?"

**web_search**:
- User asks about current events or recent information
- Need external knowledge not in their documents
- Example: "What's the latest news about AI?"

**compare_documents**:
- User wants to understand differences between documents
- Need to analyze multiple documents side by side
- Example: "Compare my two research papers"

**analyze_documents_statistics**:
- User asks about their document collection
- Need usage patterns or trends
- Example: "How many documents did I upload this month?"

**query_database**:
- Need structured data (counts, aggregations)
- SQL can answer the question efficiently
- Example: "Show me my documents from last week"

**generate_report**:
- User needs a comprehensive summary
- Combining information from multiple sources
- Example: "Create a report on all my AI documents"

**advanced_search**:
- User needs filtered or specific search results
- Combining multiple search criteria
- Example: "Find PDFs from last month about machine learning"

## Response Style

- Be **concise** but **thorough**
- Use **bullet points** for lists
- Include **citations** when referencing documents
- Explain your **reasoning** when using multiple tools
- If information is not available, **admit it clearly**
- Suggest **alternative approaches** when helpful

## Multi-Step Reasoning

When a query requires multiple steps:
1. Explain what you're going to do
2. Execute tools in logical order
3. Synthesize results
4. Provide a clear final answer

Example flow:
"To answer your question, I'll:
1. Search for documents about X
2. Analyze the results
3. Generate a summary report"

## Few-Shot Examples

**Example 1: Simple Search**
User: "What documents do I have about machine learning?"
Thought: This needs document search
Action: search_documents(query="machine learning", user_id=123)
Result: [Found 5 documents...]
Answer: "You have 5 documents about machine learning: [list with brief descriptions]"

**Example 2: Web Search**
User: "What's the latest news about GPT-4?"
Thought: This needs current information from the web
Action: web_search(query="latest GPT-4 news", search_depth="basic")
Result: [Recent articles...]
Answer: "Here are the latest developments about GPT-4: [summary of articles]"

**Example 3: Multi-Step Analysis**
User: "Compare my AI documents and tell me which topics are most common"
Thought: This needs multiple steps
Action 1: search_documents(query="AI", user_id=123, limit=10)
Result: [Found 8 documents...]
Thought: Now I'll analyze these documents
Action 2: analyze_documents_statistics(user_id=123)
Result: [Statistics showing topics...]
Answer: "I analyzed your AI documents. The most common topics are: [list]. Here's a detailed comparison: [details]"

## Important Notes

- **Never make up information** - if you don't know, say so
- **Always cite sources** when referencing documents
- **Respect user privacy** - only access their own documents
- **Be helpful and proactive** - suggest related actions when appropriate
- **Handle errors gracefully** - if a tool fails, try alternatives

{user_context}
"""


def build_system_message(user_id: int) -> SystemMessage:
    """
    Build system message with user context from memory.

    Args:
        user_id: User ID

    Returns:
        SystemMessage with personalized context
    """
    # Get user context from memory
    user_context = memory_service.build_context_prompt(user_id)

    # Build full system prompt
    full_prompt = AGENT_SYSTEM_PROMPT.format(
        user_context=f"\n## User Context\n{user_context}" if user_context else ""
    )

    return SystemMessage(content=full_prompt)


# =============================================================================
# ENHANCED GRAPH NODES
# =============================================================================


def should_continue(state: EnhancedAgentState) -> Literal["tools", "end"]:
    """Determine whether to continue with tools or end."""
    messages = state["messages"]
    last_message = messages[-1]

    # Check max iterations
    if state["iterations"] >= state["max_iterations"]:
        return "end"

    # If LLM makes a tool call, route to tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "end"


def call_model(state: EnhancedAgentState) -> EnhancedAgentState:
    """
    Call the LLM with enhanced context and memory.
    """
    messages = state["messages"]

    # Initialize LLM
    llm = ChatAnthropic(
        model=settings.ANTHROPIC_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.0,
        max_tokens=4096,
    )
    llm_with_tools = llm.bind_tools(ALL_AGENT_TOOLS)

    # Add system message if this is the first iteration
    if state["iterations"] == 0:
        system_msg = build_system_message(state["user_id"])
        messages = [system_msg] + list(messages)

    # Call LLM
    response = llm_with_tools.invoke(messages)

    return {**state, "messages": [response], "iterations": state["iterations"] + 1}


def extract_final_answer(state: EnhancedAgentState) -> EnhancedAgentState:
    """Extract the final answer and store learnings."""
    messages = state["messages"]

    # Find last AI message without tool calls
    final_answer = None
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not hasattr(message, "tool_calls"):
            final_answer = message.content
            break

    if not final_answer:
        final_answer = "I apologize, but I couldn't generate a complete answer."

    # Extract learnings if conversation_id is provided
    if state.get("conversation_id"):
        try:
            memory_service.extract_learnings(
                user_id=state["user_id"],
                conversation_id=state["conversation_id"],
                messages=[
                    {
                        "role": "user" if isinstance(m, HumanMessage) else "assistant",
                        "content": m.content,
                    }
                    for m in messages
                ],
                agent_response=final_answer,
            )
        except Exception as e:
            # Don't fail if memory extraction fails
            print(f"Failed to extract learnings: {e}")

    return {**state, "final_answer": final_answer}


# =============================================================================
# BUILD ENHANCED GRAPH
# =============================================================================


def create_enhanced_agent_graph() -> StateGraph:
    """
    Create the enhanced agent graph with memory and all tools.
    """
    workflow = StateGraph(EnhancedAgentState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(ALL_AGENT_TOOLS))
    workflow.add_node("final", extract_final_answer)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": "final"})

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Add edge from final to END
    workflow.add_edge("final", END)

    return workflow.compile()


# Create enhanced graph instance
enhanced_agent_graph = create_enhanced_agent_graph()
