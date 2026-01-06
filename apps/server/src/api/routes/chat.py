"""Chat endpoints."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.core.claude import claude_client
from src.services.analyzer import AnalyzerService

router = APIRouter()

# In-memory chat history (use Redis in production)
chat_history: dict[str, list[dict[str, Any]]] = {}


class ChatMessage(BaseModel):
    """Chat message schema."""

    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Chat response schema."""

    id: str
    message: str
    response: str
    timestamp: datetime


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatMessage,
    db: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """Chat with Observer AI."""
    message_id = str(uuid4())

    # Get context from recent activity
    analyzer = AnalyzerService(db)
    activity_context = await analyzer.get_summary()

    # Build system prompt with context
    system_prompt = f"""You are Observer, a personal AI assistant that helps users understand their work patterns and suggests automations.

Current activity context:
- Total events today: {activity_context.get('total_events', 0)}
- Top apps: {', '.join([app[0] for app in activity_context.get('top_apps', [])[:5]])}
- Categories: {activity_context.get('categories', {})}

Be helpful, concise, and proactive in suggesting improvements. When appropriate, suggest creating automation agents for repetitive tasks."""

    # Get response from Claude
    try:
        response = await claude_client.complete(
            prompt=data.message,
            system=system_prompt,
        )
    except Exception as e:
        response = f"I'm having trouble connecting to my AI backend. Error: {str(e)}"

    # Store in history
    session_id = data.context.get("session_id", "default")
    if session_id not in chat_history:
        chat_history[session_id] = []

    timestamp = datetime.now(timezone.utc)
    chat_history[session_id].append({
        "id": message_id,
        "role": "user",
        "content": data.message,
        "timestamp": timestamp.isoformat(),
    })
    chat_history[session_id].append({
        "id": str(uuid4()),
        "role": "assistant",
        "content": response,
        "timestamp": timestamp.isoformat(),
    })

    return ChatResponse(
        id=message_id,
        message=data.message,
        response=response,
        timestamp=timestamp,
    )


@router.get("/history")
async def get_chat_history(
    session_id: str = "default",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get chat history."""
    history = chat_history.get(session_id, [])
    return history[-limit:]


@router.delete("/history")
async def clear_chat_history(
    session_id: str = "default",
) -> dict[str, str]:
    """Clear chat history."""
    if session_id in chat_history:
        del chat_history[session_id]
    return {"message": "Chat history cleared"}
