"""Chat endpoints with PostgreSQL storage, Redis caching, and Memory integration."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.core.claude import claude_client
from src.core.config import settings
from src.core.logging import get_logger, log_error
from src.core.security import validate_session_id
from src.db.models import ChatMessage
from src.services.analyzer import AnalyzerService
from src.services.memory import MemoryManager

logger = get_logger(__name__)

router = APIRouter()

# Redis client for caching
redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """Get Redis client, create if needed."""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            log_error(
                logger,
                "Failed to connect to Redis",
                error=e,
                extra={"event_type": "redis_connection_error"},
            )
            redis_client = None
    return redis_client


class ChatMessageInput(BaseModel):
    """Chat message input schema."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User message content",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the message",
    )


class ChatResponse(BaseModel):
    """Chat response schema."""

    id: str
    message: str
    response: str
    timestamp: datetime


class ChatMessageOutput(BaseModel):
    """Chat message output schema."""

    id: str
    role: str
    content: str
    timestamp: str


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatMessageInput,
    db: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """Chat with Observer AI with Memory integration."""
    message_id = str(uuid4())
    session_id = data.context.get("session_id", "default")

    # Validate session_id to prevent session forgery
    session_id = validate_session_id(session_id)

    # Use naive datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE column
    timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

    # Get context from recent activity
    analyzer = AnalyzerService(db)
    activity_context = await analyzer.get_summary()

    # Get memory context (Memory System 2026)
    memory_manager = MemoryManager(db, session_id)
    memory_context: dict[str, Any] = {}
    memory_prompt_section = ""

    try:
        memory_context = await memory_manager.build_context_for_query(data.message)
        memory_prompt_section = await memory_manager.format_context_for_prompt(memory_context)
    except Exception as e:
        log_error(
            logger,
            "Failed to get memory context",
            error=e,
            extra={
                "event_type": "memory_context_error",
                "session_id": session_id,
            },
        )

    # Build system prompt with activity and memory context
    system_prompt = (
        "You are Observer, a personal AI assistant that helps users "
        "understand their work patterns and suggests automations.\n\n"
    )

    # Add memory context if available
    if memory_prompt_section:
        system_prompt += f"# MEMORY CONTEXT\n{memory_prompt_section}\n\n"

    system_prompt += (
        f"# CURRENT ACTIVITY\n"
        f"- Total events today: {activity_context.get('total_events', 0)}\n"
        f"- Top apps: {', '.join([app[0] for app in activity_context.get('top_apps', [])[:5]])}\n"
        f"- Categories: {activity_context.get('categories', {})}\n\n"
        "Be helpful, concise, and proactive in suggesting improvements. "
        "Use your memory of the user to personalize responses. "
        "Respond in Russian. When appropriate, suggest creating automation agents."
    )

    # Load conversation history from database
    history_query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
        .limit(100)  # Keep full history
    )
    history_result = await db.execute(history_query)
    history_messages = history_result.scalars().all()

    # Build messages array with smart truncation to prevent 413
    # Keep recent messages (last 20) in full, truncate older ones
    max_total_history_chars = 30000  # ~30k chars for history
    max_message_chars = 2000  # Max chars per message

    messages = []
    total_chars = 0
    msg_list = list(history_messages)

    # Always keep the most recent 20 messages in full
    recent_threshold = max(0, len(msg_list) - 20)

    for i, msg in enumerate(msg_list):
        content = msg.content

        # Truncate older messages more aggressively
        if i < recent_threshold:
            if len(content) > 500:
                content = content[:500] + "..."

        # Ensure no single message is too long
        if len(content) > max_message_chars:
            content = content[:max_message_chars] + "..."

        # Skip if we've exceeded total limit (but always keep last 10)
        if total_chars + len(content) > max_total_history_chars and i < len(msg_list) - 10:
            continue

        messages.append({"role": msg.role, "content": content})
        total_chars += len(content)

    messages.append({"role": "user", "content": data.message})

    # Get response from Claude with full conversation history
    # Auto-retry with reduced context on 413 error
    response = None
    retry_count = 0
    max_retries = 3
    current_messages = messages.copy()
    current_system = system_prompt

    while response is None and retry_count < max_retries:
        try:
            response = await claude_client.complete(
                messages=current_messages,
                system=current_system,
            )
            logger.info(
                "Claude response generated",
                extra={
                    "event_type": "claude_response",
                    "session_id": session_id,
                    "response_length": len(response),
                    "retry_count": retry_count,
                },
            )
        except Exception as e:
            error_str = str(e)
            retry_count += 1

            # On 413, reduce context and retry
            is_too_large = "413" in error_str or "too large" in error_str.lower()
            if is_too_large and retry_count < max_retries:
                logger.warning(
                    f"Context too large, reducing and retrying ({retry_count}/{max_retries})",
                    extra={"event_type": "context_reduction", "session_id": session_id},
                )
                # Reduce messages - keep only last half
                if len(current_messages) > 4:
                    half = len(current_messages) // 2
                    current_messages = current_messages[half:]
                # Reduce system prompt
                if len(current_system) > 2000:
                    truncated = current_system[:2000]
                    current_system = truncated + "\n[Context reduced]"
                continue

            log_error(
                logger,
                "Failed to get Claude response",
                error=e,
                extra={
                    "event_type": "claude_error",
                    "session_id": session_id,
                    "retry_count": retry_count,
                },
            )
            # Provide user-friendly error message
            if "413" in error_str or "too large" in error_str.lower():
                response = (
                    "Извините, контекст беседы слишком большой. "
                    "Попробуйте очистить историю чата."
                )
            elif "rate" in error_str.lower() or "429" in error_str:
                response = (
                    "Превышен лимит запросов. "
                    "Пожалуйста, подождите немного и попробуйте снова."
                )
            elif "timeout" in error_str.lower():
                response = (
                    "Превышено время ожидания ответа. "
                    "Пожалуйста, попробуйте снова."
                )
            else:
                response = (
                    "Извините, произошла ошибка при подключении к AI. "
                    "Пожалуйста, попробуйте снова."
                )

    # Store user message in database
    user_msg = ChatMessage(
        id=uuid4(),
        session_id=session_id,
        role="user",
        content=data.message,
        timestamp=timestamp,
    )
    db.add(user_msg)

    # Store assistant message in database with slight offset for proper ordering
    assistant_timestamp = timestamp + timedelta(milliseconds=100)
    assistant_msg = ChatMessage(
        id=uuid4(),
        session_id=session_id,
        role="assistant",
        content=response,
        timestamp=assistant_timestamp,
    )
    db.add(assistant_msg)

    try:
        await db.commit()
        logger.info(
            "Chat messages saved",
            extra={
                "event_type": "chat_saved",
                "session_id": session_id,
                "message_count": 2,
            },
        )
    except Exception as e:
        log_error(
            logger,
            "Failed to save chat messages",
            error=e,
            extra={
                "event_type": "chat_save_error",
                "session_id": session_id,
            },
        )
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to save chat messages"
        ) from e

    # Invalidate cache for this session
    r = await get_redis()
    if r:
        try:
            await r.delete(f"chat_history:{session_id}")
            logger.debug(
                "Cache invalidated",
                extra={"event_type": "cache_invalidated", "session_id": session_id},
            )
        except Exception as e:
            log_error(
                logger,
                "Failed to invalidate cache",
                error=e,
                extra={"event_type": "cache_error", "session_id": session_id},
            )

    # Process interaction for memory (async, non-blocking)
    try:
        await memory_manager.process_interaction(
            user_message=data.message,
            assistant_response=response,
            message_id=user_msg.id,
            context=memory_context,
        )
        logger.debug(
            "Memory processed",
            extra={"event_type": "memory_processed", "session_id": session_id},
        )
    except Exception as e:
        log_error(
            logger,
            "Error processing memory",
            error=e,
            extra={"event_type": "memory_processing_error", "session_id": session_id},
        )
        # Don't fail the chat request if memory processing fails

    return ChatResponse(
        id=message_id,
        message=data.message,
        response=response,
        timestamp=timestamp,
    )


@router.get("/history")
async def get_chat_history(
    session_id: str = Query(
        default="default",
        min_length=1,
        max_length=255,
        description="Session identifier",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of messages to return",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[ChatMessageOutput]:
    """Get chat history from database with Redis caching."""
    # Validate session_id to prevent session forgery
    session_id = validate_session_id(session_id)

    cache_key = f"chat_history:{session_id}"

    # Try to get from Redis cache first
    r = await get_redis()
    if r:
        try:
            cached = await r.get(cache_key)
            if cached:
                logger.debug(
                    "Cache hit for chat history",
                    extra={"event_type": "cache_hit", "session_id": session_id},
                )
                return json.loads(cached)
        except Exception as e:
            log_error(
                logger,
                "Cache read error",
                error=e,
                extra={"event_type": "cache_read_error", "session_id": session_id},
            )

    # Get from database
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    # Convert to output format (reverse to get chronological order)
    history = [
        ChatMessageOutput(
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp.isoformat(),
        )
        for msg in reversed(messages)
    ]

    # Cache in Redis for 5 minutes
    if r and history:
        try:
            await r.setex(
                cache_key,
                300,  # 5 minutes TTL
                json.dumps([h.model_dump() for h in history]),
            )
            logger.debug(
                "Chat history cached",
                extra={
                    "event_type": "cache_write",
                    "session_id": session_id,
                    "message_count": len(history),
                },
            )
        except Exception as e:
            log_error(
                logger,
                "Cache write error",
                error=e,
                extra={"event_type": "cache_write_error", "session_id": session_id},
            )

    return history


@router.delete("/history")
async def clear_chat_history(
    session_id: str = Query(
        default="default",
        min_length=1,
        max_length=255,
        description="Session identifier",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Clear chat history from database."""
    from sqlalchemy import delete

    # Validate session_id to prevent session forgery
    session_id = validate_session_id(session_id)

    # Delete from database
    stmt = delete(ChatMessage).where(ChatMessage.session_id == session_id)
    result = await db.execute(stmt)
    await db.commit()

    logger.info(
        "Chat history cleared",
        extra={
            "event_type": "chat_history_cleared",
            "session_id": session_id,
            "rows_deleted": result.rowcount,
        },
    )

    # Clear cache
    r = await get_redis()
    if r:
        try:
            await r.delete(f"chat_history:{session_id}")
        except Exception as e:
            log_error(
                logger,
                "Failed to clear cache",
                error=e,
                extra={"event_type": "cache_clear_error", "session_id": session_id},
            )

    return {"message": "Chat history cleared"}
