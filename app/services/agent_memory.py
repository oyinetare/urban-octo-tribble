# app/services/agent_memory.py
"""
Agent memory system for maintaining conversation context and user preferences.
"""

import json
from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Field, select

from app.core.database import get_session
from app.models.base import BaseModel

# =============================================================================
# MEMORY MODELS
# =============================================================================


class ConversationMemory(BaseModel, table=True):
    """
    Long-term conversation memory.
    Stores important facts and context from conversations.
    """

    __tablename__ = "conversation_memory"

    user_id: int = Field(foreign_key="user.id", index=True)
    conversation_id: int | None = Field(default=None, foreign_key="query.id")
    memory_type: str = Field(index=True)  # fact, preference, context
    key: str = Field(index=True)  # e.g., "favorite_topic", "recent_interest"
    value: str  # JSON serialized value
    importance: float = Field(default=0.5)  # 0.0 to 1.0
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


class UserPreference(BaseModel, table=True):
    """
    User preferences for agent behavior.
    """

    __tablename__ = "user_preferences"

    user_id: int = Field(foreign_key="user.id", index=True, unique=True)

    # Communication preferences
    response_style: str = Field(default="balanced")  # concise, balanced, detailed
    preferred_language: str = Field(default="en")
    tone: str = Field(default="professional")  # casual, professional, technical

    # Agent behavior
    proactive_suggestions: bool = Field(default=True)
    web_search_enabled: bool = Field(default=True)
    max_iterations: int = Field(default=10)

    # Notification preferences
    notify_on_completion: bool = Field(default=True)
    notify_on_insights: bool = Field(default=False)

    # Custom preferences (JSON)
    custom_settings: str = Field(default="{}")  # JSON string


# =============================================================================
# MEMORY SERVICE
# =============================================================================


class AgentMemoryService:
    """
    Service for managing agent memory and context.
    """

    def __init__(self):
        self.short_term_memory = {}  # In-memory cache for current session

    # -------------------------------------------------------------------------
    # SHORT-TERM MEMORY (Current Session)
    # -------------------------------------------------------------------------

    def add_to_short_term(
        self, user_id: int, key: str, value: Any, ttl_seconds: int = 3600
    ) -> None:
        """
        Add to short-term memory (current session).

        Args:
            user_id: User ID
            key: Memory key
            value: Value to store
            ttl_seconds: Time to live in seconds
        """
        if user_id not in self.short_term_memory:
            self.short_term_memory[user_id] = {}

        self.short_term_memory[user_id][key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl_seconds),
        }

    def get_from_short_term(self, user_id: int, key: str) -> Any | None:
        """Get from short-term memory."""
        if user_id not in self.short_term_memory:
            return None

        memory = self.short_term_memory[user_id].get(key)
        if not memory:
            return None

        # Check expiry
        if memory["expires_at"] < datetime.utcnow():
            del self.short_term_memory[user_id][key]
            return None

        return memory["value"]

    def clear_short_term(self, user_id: int) -> None:
        """Clear short-term memory for user."""
        if user_id in self.short_term_memory:
            del self.short_term_memory[user_id]

    # -------------------------------------------------------------------------
    # LONG-TERM MEMORY (Database)
    # -------------------------------------------------------------------------

    def store_memory(
        self,
        user_id: int,
        memory_type: str,
        key: str,
        value: Any,
        importance: float = 0.5,
        conversation_id: int | None = None,
        ttl_days: int | None = None,
    ) -> ConversationMemory:
        """
        Store in long-term memory.

        Args:
            user_id: User ID
            memory_type: Type of memory (fact, preference, context)
            key: Memory key
            value: Value to store (will be JSON serialized)
            importance: Importance score (0.0 to 1.0)
            conversation_id: Associated conversation ID
            ttl_days: Days until memory expires (None = never)

        Returns:
            Created ConversationMemory object
        """
        with next(get_session()) as session:
            # Check if memory exists
            existing = session.exec(
                select(ConversationMemory).where(
                    ConversationMemory.user_id == user_id, ConversationMemory.key == key
                )
            ).first()

            if existing:
                # Update existing memory
                existing.value = json.dumps(value)
                existing.importance = importance
                existing.last_accessed = datetime.utcnow()
                if ttl_days:
                    existing.expires_at = datetime.utcnow() + timedelta(days=ttl_days)
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing

            # Create new memory
            memory = ConversationMemory(
                user_id=user_id,
                conversation_id=conversation_id,
                memory_type=memory_type,
                key=key,
                value=json.dumps(value),
                importance=importance,
                expires_at=datetime.utcnow() + timedelta(days=ttl_days) if ttl_days else None,
            )

            session.add(memory)
            session.commit()
            session.refresh(memory)
            return memory

    def recall_memory(self, user_id: int, key: str) -> Any | None:
        """
        Recall a specific memory.

        Args:
            user_id: User ID
            key: Memory key

        Returns:
            Stored value or None if not found
        """
        with next(get_session()) as session:
            memory = session.exec(
                select(ConversationMemory).where(
                    ConversationMemory.user_id == user_id, ConversationMemory.key == key
                )
            ).first()

            if not memory:
                return None

            # Check expiry
            if memory.expires_at and memory.expires_at < datetime.utcnow():
                session.delete(memory)
                session.commit()
                return None

            # Update last accessed
            memory.last_accessed = datetime.utcnow()
            session.add(memory)
            session.commit()

            return json.loads(memory.value)

    def recall_by_type(self, user_id: int, memory_type: str, limit: int = 10) -> list[dict]:
        """
        Recall memories by type, ordered by importance and recency.

        Args:
            user_id: User ID
            memory_type: Type of memory to recall
            limit: Maximum number of memories to return

        Returns:
            List of memory dictionaries
        """
        with next(get_session()) as session:
            memories = session.exec(
                select(ConversationMemory)
                .where(
                    ConversationMemory.user_id == user_id,
                    ConversationMemory.memory_type == memory_type,
                )
                .order_by(
                    ConversationMemory.importance.desc(), ConversationMemory.last_accessed.desc()
                )
                .limit(limit)
            ).all()

            return [
                {
                    "key": m.key,
                    "value": json.loads(m.value),
                    "importance": m.importance,
                    "last_accessed": m.last_accessed.isoformat() if m.last_accessed else None,
                }
                for m in memories
                if not m.expires_at or m.expires_at > datetime.utcnow()
            ]

    def forget_memory(self, user_id: int, key: str) -> bool:
        """
        Delete a memory.

        Args:
            user_id: User ID
            key: Memory key

        Returns:
            True if deleted, False if not found
        """
        with next(get_session()) as session:
            memory = session.exec(
                select(ConversationMemory).where(
                    ConversationMemory.user_id == user_id, ConversationMemory.key == key
                )
            ).first()

            if not memory:
                return False

            session.delete(memory)
            session.commit()
            return True

    def cleanup_expired(self) -> int:
        """
        Remove expired memories.

        Returns:
            Number of memories deleted
        """
        with next(get_session()) as session:
            expired = session.exec(
                select(ConversationMemory).where(ConversationMemory.expires_at < datetime.utcnow())
            ).all()

            count = len(expired)
            for memory in expired:
                session.delete(memory)

            session.commit()
            return count

    # -------------------------------------------------------------------------
    # USER PREFERENCES
    # -------------------------------------------------------------------------

    def get_preferences(self, user_id: int) -> UserPreference:
        """
        Get user preferences, creating default if not exists.

        Args:
            user_id: User ID

        Returns:
            UserPreference object
        """
        with next(get_session()) as session:
            prefs = session.exec(
                select(UserPreference).where(UserPreference.user_id == user_id)
            ).first()

            if not prefs:
                prefs = UserPreference(user_id=user_id)
                session.add(prefs)
                session.commit()
                session.refresh(prefs)

            return prefs

    def update_preferences(self, user_id: int, **kwargs) -> UserPreference:
        """
        Update user preferences.

        Args:
            user_id: User ID
            **kwargs: Preference fields to update

        Returns:
            Updated UserPreference object
        """
        with next(get_session()) as session:
            prefs = self.get_preferences(user_id)

            for key, value in kwargs.items():
                if hasattr(prefs, key):
                    setattr(prefs, key, value)

            session.add(prefs)
            session.commit()
            session.refresh(prefs)
            return prefs

    # -------------------------------------------------------------------------
    # CONTEXT BUILDING
    # -------------------------------------------------------------------------

    def build_context_prompt(self, user_id: int) -> str:
        """
        Build a context prompt from user's memory and preferences.

        This prompt is prepended to agent conversations to provide context.

        Args:
            user_id: User ID

        Returns:
            Context prompt string
        """
        # Get preferences
        prefs = self.get_preferences(user_id)

        # Get recent facts
        recent_facts = self.recall_by_type(user_id, "fact", limit=5)

        # Get user preferences (stored as memories)
        user_prefs = self.recall_by_type(user_id, "preference", limit=3)

        # Build context
        context_parts = []

        # Communication style
        context_parts.append(f"Communication style: {prefs.response_style}")
        if prefs.tone:
            context_parts.append(f"Tone: {prefs.tone}")

        # Recent facts about user
        if recent_facts:
            facts_str = ", ".join([f"{f['key']}: {f['value']}" for f in recent_facts[:3]])
            context_parts.append(f"Recent context: {facts_str}")

        # User preferences
        if user_prefs:
            prefs_str = ", ".join([f"{p['key']}: {p['value']}" for p in user_prefs])
            context_parts.append(f"User preferences: {prefs_str}")

        # Proactive suggestions
        if not prefs.proactive_suggestions:
            context_parts.append("Note: User prefers minimal proactive suggestions")

        return "\n".join(context_parts)

    def extract_learnings(
        self, user_id: int, conversation_id: int, messages: list, agent_response: str
    ) -> None:
        """
        Extract and store learnings from a conversation.

        This analyzes the conversation to identify:
        - User preferences
        - Important facts
        - Topics of interest

        Args:
            user_id: User ID
            conversation_id: Conversation ID
            messages: List of conversation messages
            agent_response: Agent's final response
        """
        # Extract topics mentioned
        # (In production, use NER or LLM for extraction)

        # Simple keyword extraction (placeholder)
        user_messages = [m for m in messages if m.get("role") == "user"]

        if len(user_messages) > 0:
            last_message = user_messages[-1].get("content", "")

            # Store as recent interest
            self.store_memory(
                user_id=user_id,
                memory_type="context",
                key="last_query",
                value=last_message,
                importance=0.6,
                conversation_id=conversation_id,
                ttl_days=30,
            )

            # Detect patterns (placeholder)
            # In production, use ML/NLP
            if "search" in last_message.lower():
                self.store_memory(
                    user_id=user_id,
                    memory_type="preference",
                    key="frequently_searches",
                    value=True,
                    importance=0.7,
                    ttl_days=90,
                )


# Create singleton
memory_service = AgentMemoryService()
