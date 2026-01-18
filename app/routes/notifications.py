from collections.abc import Awaitable
from datetime import datetime
from typing import cast

from fastapi import APIRouter, Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from app.core.notification import NotificationService
from app.dependencies import (
    get_admin_user,
    get_current_active_user,
    get_notification_service,
    get_session,
)
from app.exceptions import AppException
from app.models import Notification, User
from app.schemas import NotificationCreate

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", status_code=201)
async def create_notification(
    notification_data: NotificationCreate,
    session: AsyncSession = Depends(get_session),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Create notification and trigger delivery via all channels.

    This is an INTERNAL endpoint - should only be called by your
    application's services (document upload, URL click, etc.).

    In production, protect this with:
    - IP whitelist
    - Internal service token
    - Separate internal API gateway

    Args:
        notification_data: Notification details

    Returns:
        Created notification with delivery status

    Example:
        POST /api/v1/notifications
        {
            "user_id": 123,
            "type": "document_uploaded",
            "title": "Document Ready",
            "message": "Your document 'Report.pdf' is ready",
            "action_url": "/documents/456"
        }
    """
    # Create notification in database
    notification = Notification(
        user_id=notification_data.user_id,
        type=notification_data.type,
        title=notification_data.title,
        message=notification_data.message,
        action_url=notification_data.action_url,
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)

    channel_results = await notification_service.notify(notification)

    return {
        "success": True,
        "notification_id": notification.id,
        "channels": channel_results,
        "message": "Notification created and delivery tasks enqueued",
    }


@router.get("/")
async def list_notifications(
    skip: int = 0,
    limit: int = 20,
    unread_only: bool = False,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """List user's notifications (paginated)."""
    limit = min(limit, 100)

    statement = select(Notification).where(Notification.user_id == current_user.id)

    if unread_only:
        statement = statement.where(col(Notification.read_at).is_(None))

    statement = statement.order_by(col(Notification.created_at).desc()).offset(skip).limit(limit)

    result = await session.execute(statement)
    notifications = result.scalars().all()

    return {
        "success": True,
        "count": len(notifications),
        "skip": skip,
        "limit": limit,
        "notifications": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "action_url": n.action_url,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
    }


@router.get("/unread")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Get count of unread notifications."""
    statement = select(func.count(Notification.id)).where(
        Notification.user_id == current_user.id,
        col(Notification.read_at).is_(None),
    )

    result = await session.execute(statement)
    count = result.scalar()

    return {
        "success": True,
        "unread_count": count or 0,
    }


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Mark notification as read."""
    statement = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    )
    result = await session.execute(statement)
    notification = result.scalar_one_or_none()

    if not notification:
        raise AppException(status_code=404, message="Notification not found")

    notification.read_at = datetime.now()
    session.add(notification)
    await session.commit()

    return {
        "success": True,
        "notification_id": notification.id,
        "read_at": notification.read_at.isoformat(),
    }


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Mark all notifications as read."""
    # ✅ Fix: Use separate where clauses for update
    statement = (
        update(Notification)
        .where(
            col(Notification.user_id == current_user.id),
            col(Notification.read_at).is_(None),
        )
        .values(read_at=datetime.now())
    )

    result = await session.execute(statement)
    await session.commit()

    rows_updated = result.rowcount if hasattr(result, "rowcount") else 0

    return {
        "success": True,
        "marked_read": rows_updated,
    }


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete notification."""
    statement = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    )
    result = await session.execute(statement)
    notification = result.scalar_one_or_none()

    if not notification:
        raise AppException(status_code=404, message="Notification not found")

    await session.delete(notification)
    await session.commit()

    return {
        "success": True,
        "notification_id": notification_id,
        "message": "Notification deleted",
    }


# ADMIN API - Dead Letter Queue Management - to view DLQ and retry failed webhooks
@router.get("/admin/dlq")
async def view_dead_letter_queue(
    current_user: User = Depends(get_admin_user),
):
    """
    View failed webhooks in dead letter queue (admin only).

    Requires:
        Admin role

    Returns:
        List of failed webhook entries

    Example:
        GET /api/v1/notifications/admin/dlq
    """
    from app.core import redis_service

    if not redis_service.is_available or not redis_service.client:
        raise AppException(status_code=503, message="Redis unavailable")

    import json

    dlq_entries_json = await cast(
        Awaitable[list],
        redis_service.client.lrange("queue:webhooks:dlq", 0, -1),
    )

    dlq_entries = [json.loads(entry) for entry in dlq_entries_json]

    return {
        "success": True,
        "count": len(dlq_entries),
        "entries": dlq_entries,
    }


@router.post("/admin/dlq/retry")
async def retry_dead_letter_queue(
    current_user: User = Depends(get_admin_user),
):
    """
    Retry all failed webhooks in dead letter queue (admin only).

    This enqueues a background task that will:
    1. Pop all entries from DLQ
    2. Re-enqueue them to main webhook queue
    3. Return statistics

    Requires:
        Admin role

    Returns:
        Task ID for tracking retry job

    Example:
        POST /api/v1/notifications/admin/dlq/retry
    """
    from app.tasks.webhook_tasks import retry_dlq_webhooks_task

    task = await retry_dlq_webhooks_task.kiq()

    return {
        "success": True,
        "message": "DLQ retry task enqueued",
        "task_id": task.task_id,
    }


@router.delete("/admin/dlq/clear")
async def clear_dead_letter_queue(
    current_user: User = Depends(get_admin_user),
):
    """
    Clear all entries from dead letter queue (admin only).

    ⚠️  WARNING: This permanently deletes all failed webhook entries!

    Requires:
        Admin role

    Returns:
        Number of entries deleted

    Example:
        DELETE /api/v1/notifications/admin/dlq/clear
    """
    from app.core import redis_service

    if not redis_service.is_available or not redis_service.client:
        raise AppException(status_code=503, message="Redis unavailable")

    size = await cast(
        Awaitable[int],
        redis_service.client.llen("queue:webhooks:dlq"),
    )

    await redis_service.client.delete("queue:webhooks:dlq")

    return {
        "success": True,
        "deleted": size,
        "message": f"Deleted {size} entries from DLQ",
    }
