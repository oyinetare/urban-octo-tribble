# app/routes/memory.py
"""
API routes for agent memory and user preferences.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.agent import MemoryCreate, MemoryResponse, PreferencesResponse, PreferencesUpdate
from app.services.agent_memory import memory_service

router = APIRouter()


@router.post("/store", response_model=dict)
async def store_memory(memory: MemoryCreate, current_user: User = Depends(get_current_user)):
    """
    Store a new memory or update existing one.

    Memory types:
    - **fact**: Important facts about the user (e.g., "works on AI research")
    - **preference**: User preferences (e.g., "prefers concise answers")
    - **context**: Contextual information (e.g., "recently asked about topic X")
    """
    try:
        stored = memory_service.store_memory(
            user_id=current_user.id,
            memory_type=memory.memory_type,
            key=memory.key,
            value=memory.value,
            importance=memory.importance,
            ttl_days=memory.ttl_days,
        )

        return {
            "status": "success",
            "message": "Memory stored successfully",
            "memory_id": stored.id,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {str(e)}")


@router.get("/recall/{key}")
async def recall_memory(key: str, current_user: User = Depends(get_current_user)):
    """
    Recall a specific memory by key.
    """
    value = memory_service.recall_memory(current_user.id, key)

    if value is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"key": key, "value": value}


@router.get("/list", response_model=list[MemoryResponse])
async def list_memories(
    memory_type: Literal["fact", "preference", "context"] | None = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    """
    List all memories, optionally filtered by type.
    """
    if memory_type:
        memories = memory_service.recall_by_type(current_user.id, memory_type, limit=limit)
    else:
        # Get all types
        memories = []
        for mtype in ["fact", "preference", "context"]:
            memories.extend(memory_service.recall_by_type(current_user.id, mtype, limit=limit))

        # Sort by importance
        memories = sorted(memories, key=lambda x: x["importance"], reverse=True)[:limit]

    return memories


@router.delete("/forget/{key}")
async def forget_memory(key: str, current_user: User = Depends(get_current_user)):
    """
    Delete a specific memory.
    """
    success = memory_service.forget_memory(current_user.id, key)

    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"status": "success", "message": f"Memory '{key}' deleted"}


@router.delete("/clear")
async def clear_all_memories(
    memory_type: Literal["fact", "preference", "context"] | None = None,
    current_user: User = Depends(get_current_user),
):
    """
    Clear all memories, optionally filtered by type.

    **Warning**: This action cannot be undone.
    """
    # Get memories to delete
    from sqlmodel import select

    from app.core.database import get_session
    from app.services.agent_memory import ConversationMemory

    with next(get_session()) as session:
        query = select(ConversationMemory).where(ConversationMemory.user_id == current_user.id)

        if memory_type:
            query = query.where(ConversationMemory.memory_type == memory_type)

        memories = session.exec(query).all()
        count = len(memories)

        for memory in memories:
            session.delete(memory)

        session.commit()

    return {"status": "success", "message": f"Cleared {count} memories"}


# =============================================================================
# PREFERENCES ENDPOINTS
# =============================================================================


@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(current_user: User = Depends(get_current_user)):
    """
    Get current user preferences.
    """
    prefs = memory_service.get_preferences(current_user.id)

    return PreferencesResponse(
        user_id=prefs.user_id,
        response_style=prefs.response_style,
        preferred_language=prefs.preferred_language,
        tone=prefs.tone,
        proactive_suggestions=prefs.proactive_suggestions,
        web_search_enabled=prefs.web_search_enabled,
        max_iterations=prefs.max_iterations,
        notify_on_completion=prefs.notify_on_completion,
        notify_on_insights=prefs.notify_on_insights,
    )


@router.patch("/preferences", response_model=PreferencesResponse)
async def update_preferences(
    updates: PreferencesUpdate, current_user: User = Depends(get_current_user)
):
    """
    Update user preferences.

    Only provided fields will be updated.
    """
    # Build update dict
    update_data = {}
    for field, value in updates.dict(exclude_unset=True).items():
        if value is not None:
            update_data[field] = value

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    prefs = memory_service.update_preferences(current_user.id, **update_data)

    return PreferencesResponse(
        user_id=prefs.user_id,
        response_style=prefs.response_style,
        preferred_language=prefs.preferred_language,
        tone=prefs.tone,
        proactive_suggestions=prefs.proactive_suggestions,
        web_search_enabled=prefs.web_search_enabled,
        max_iterations=prefs.max_iterations,
        notify_on_completion=prefs.notify_on_completion,
        notify_on_insights=prefs.notify_on_insights,
    )


@router.post("/preferences/reset")
async def reset_preferences(current_user: User = Depends(get_current_user)):
    """
    Reset preferences to defaults.
    """
    from sqlmodel import select

    from app.core.database import get_session
    from app.services.agent_memory import UserPreference

    with next(get_session()) as session:
        # Delete existing preferences
        existing = session.exec(
            select(UserPreference).where(UserPreference.user_id == current_user.id)
        ).first()

        if existing:
            session.delete(existing)
            session.commit()

    # Get will create new default
    prefs = memory_service.get_preferences(current_user.id)

    return {"status": "success", "message": "Preferences reset to defaults"}


# =============================================================================
# CONTEXT ENDPOINT
# =============================================================================


@router.get("/context")
async def get_context(current_user: User = Depends(get_current_user)):
    """
    Get the current context that will be used for agent conversations.

    This shows what the agent "knows" about you.
    """
    context = memory_service.build_context_prompt(current_user.id)

    return {
        "context": context,
        "preferences": memory_service.get_preferences(current_user.id),
        "recent_memories": memory_service.recall_by_type(current_user.id, "context", limit=5),
    }
