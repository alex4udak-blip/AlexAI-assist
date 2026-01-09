"""
Persona Memory - O-Mem style holistic user profile.
Implements O-Mem's Persona Memory (PM), Working Memory (WM), and Episodic Memory (EM).
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import validate_session_id
from src.db.models.memory import (
    MemoryFact,
    MemoryKeywordIndex,
    MemoryTopic,
)

# Import sanitization function to prevent prompt injection
from src.services.memory.memory_operations import sanitize_user_input

logger = logging.getLogger(__name__)


class PersonaMemory:
    """
    O-Mem style persona memory with topic and keyword indexing.
    Features:
    - Holistic user profile (Pa - attributes, Pf - events)
    - Topic-based working memory (WM)
    - Keyword-based episodic memory (EM)
    """

    def __init__(self, db: AsyncSession, session_id: str = "default"):
        self.db = db
        # Validate session_id to prevent session forgery
        self.session_id = validate_session_id(session_id)

    # ==========================================
    # PERSONA PROFILE (Pa + Pf)
    # ==========================================

    async def get_active_profile(self) -> dict[str, Any]:
        """
        Get the active user profile.
        Combines persona attributes (Pa) and persona events (Pf).
        """
        # Get persona attributes
        attrs_result = await self.db.execute(
            select(MemoryFact).where(
                and_(
                    MemoryFact.session_id == self.session_id,
                    MemoryFact.is_persona_attribute == True,  # noqa: E712
                    MemoryFact.valid_to.is_(None),
                )
            ).order_by(MemoryFact.confidence.desc())
        )
        attributes = attrs_result.scalars().all()

        # Get persona events
        events_result = await self.db.execute(
            select(MemoryFact).where(
                and_(
                    MemoryFact.session_id == self.session_id,
                    MemoryFact.is_persona_event == True,  # noqa: E712
                )
            ).order_by(MemoryFact.event_time.desc().nullsfirst()).limit(10)
        )
        events = events_result.scalars().all()

        # Build profile
        profile = {
            "attributes": [
                {
                    "content": a.content,
                    "category": a.category,
                    "confidence": a.confidence,
                }
                for a in attributes
            ],
            "events": [
                {
                    "content": e.content,
                    "event_time": e.event_time.isoformat() if e.event_time else None,
                    "category": e.category,
                }
                for e in events
            ],
        }

        # Generate summary if we have enough data
        if len(attributes) >= 3:
            profile["summary"] = await self._generate_profile_summary(attributes, events)
        else:
            profile["summary"] = "Still learning about the user..."

        return profile

    async def _generate_profile_summary(
        self,
        attributes: list[MemoryFact],
        events: list[MemoryFact],
    ) -> str:
        """Generate a natural language summary of the user profile."""
        from src.core.claude import claude_client

        # Sanitize attribute and event content before embedding in prompt
        attrs_text = "\n".join(
            f"- {sanitize_user_input(a.content, max_length=200)} ({a.category})"
            for a in attributes[:10]
        )
        events_text = "\n".join(
            f"- {sanitize_user_input(e.content, max_length=200)}"
            for e in events[:5]
        )

        prompt = f"""Create a brief (2-3 sentences) user profile summary from these facts:

Attributes:
{attrs_text}

Recent Events:
{events_text}

Return ONLY the summary, written in third person ("The user...")."""

        try:
            summary = await claude_client.complete(
                prompt=prompt,
                system="Generate concise user profile summaries.",
            )
            return summary.strip()
        except Exception as e:
            logger.error(f"Error generating profile summary: {e}")
            return "User profile available with " + str(len(attributes)) + " known attributes."

    async def add_persona_attribute(
        self,
        content: str,
        category: str | None = None,
        confidence: float = 0.8,
    ) -> MemoryFact:
        """Add a persona attribute (Pa)."""
        fact = MemoryFact(
            id=uuid4(),
            session_id=self.session_id,
            content=content,
            fact_type="persona_attribute",
            category=category,
            is_persona_attribute=True,
            confidence=confidence,
            source="inference",
            valid_from=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(fact)
        logger.info(f"Added persona attribute: {content[:50]}...")
        return fact

    async def add_persona_event(
        self,
        content: str,
        event_time: datetime | None = None,
        category: str | None = None,
    ) -> MemoryFact:
        """Add a persona event (Pf)."""
        fact = MemoryFact(
            id=uuid4(),
            session_id=self.session_id,
            content=content,
            fact_type="persona_event",
            category=category,
            is_persona_event=True,
            event_time=event_time or datetime.now(timezone.utc).replace(tzinfo=None),
            confidence=1.0,  # Events are factual
            source="observation",
            valid_from=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(fact)
        logger.info(f"Added persona event: {content[:50]}...")
        return fact

    # ==========================================
    # WORKING MEMORY - Topic-based (WM)
    # ==========================================

    async def identify_topic(self, text: str) -> str | None:
        """Identify the main topic of text."""
        from src.core.claude import claude_client

        # Sanitize text before embedding in prompt
        sanitized_text = sanitize_user_input(text, max_length=500)

        prompt = f"""Identify the main topic of this text in 1-3 words:
"{sanitized_text}"

Return ONLY the topic (e.g., "python programming", "project planning", "health").
Return "general" if no specific topic."""

        try:
            topic = await claude_client.complete(
                prompt=prompt,
                system="Identify topics concisely.",
            )
            return topic.strip().lower()[:100]
        except Exception:
            return None

    async def get_or_create_topic(self, topic_name: str) -> MemoryTopic:
        """Get or create a topic entry."""
        result = await self.db.execute(
            select(MemoryTopic).where(
                and_(
                    MemoryTopic.session_id == self.session_id,
                    MemoryTopic.topic == topic_name,
                )
            )
        )
        topic = result.scalar_one_or_none()

        if topic:
            return topic

        # Create new topic
        topic = MemoryTopic(
            id=uuid4(),
            session_id=self.session_id,
            topic=topic_name,
            first_discussed=datetime.now(timezone.utc).replace(tzinfo=None),
            last_discussed=datetime.now(timezone.utc).replace(tzinfo=None),
            message_count=0,
        )
        self.db.add(topic)
        await self.db.flush()
        return topic

    async def index_message_to_topic(
        self,
        topic_name: str,
        message_content: str,
        message_id: UUID | None = None,
    ) -> None:
        """Index a message to a topic."""
        topic = await self.get_or_create_topic(topic_name)

        # Update topic
        topic.last_discussed = datetime.now(timezone.utc).replace(tzinfo=None)
        topic.message_count += 1

        if message_id:
            message_ids = topic.message_ids or []
            message_ids.append(message_id)
            topic.message_ids = message_ids[-100:]  # Keep last 100

    async def get_topic_context(
        self,
        topic_name: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Get context for a topic including related messages."""
        from src.db.models import ChatMessage

        topic = await self.get_or_create_topic(topic_name)

        # Get recent messages for this topic
        messages = []
        if topic.message_ids:
            result = await self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.id.in_(topic.message_ids[-limit:]))
                .order_by(ChatMessage.timestamp.desc())
            )
            for msg in result.scalars().all():
                messages.append({
                    "role": msg.role,
                    "content": msg.content[:200],
                    "timestamp": msg.timestamp.isoformat(),
                })

        return {
            "topic": topic.topic,
            "description": topic.description,
            "summary": topic.summary,
            "key_points": topic.key_points or [],
            "message_count": topic.message_count,
            "first_discussed": topic.first_discussed.isoformat() if topic.first_discussed else None,
            "last_discussed": topic.last_discussed.isoformat() if topic.last_discussed else None,
            "recent_messages": messages,
        }

    async def get_recent_topics(self, limit: int = 5) -> list[MemoryTopic]:
        """Get recently discussed topics."""
        result = await self.db.execute(
            select(MemoryTopic)
            .where(MemoryTopic.session_id == self.session_id)
            .order_by(MemoryTopic.last_discussed.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_topic_summary(self, topic_name: str) -> None:
        """Update the summary for a topic."""
        from src.core.claude import claude_client
        from src.db.models import ChatMessage

        topic = await self.get_or_create_topic(topic_name)

        if not topic.message_ids:
            return

        # Get messages for summarization
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.id.in_(topic.message_ids[-20:]))
            .order_by(ChatMessage.timestamp.asc())
        )
        messages = result.scalars().all()

        if len(messages) < 3:
            return

        # Sanitize message content before embedding in prompt
        conversation = "\n".join(
            f"{m.role}: {sanitize_user_input(m.content, max_length=200)}"
            for m in messages
        )
        # Sanitize topic name as it may come from user input
        sanitized_topic = sanitize_user_input(topic_name, max_length=100)

        prompt = f"""Summarize the key points discussed about "{sanitized_topic}":

{conversation}

Return:
1. A 1-2 sentence summary
2. 3-5 bullet points of key information

Format:
Summary: [summary here]
Key points:
- [point 1]
- [point 2]
..."""

        try:
            response = await claude_client.complete(
                prompt=prompt,
                system="Summarize conversations concisely.",
            )

            # Parse response
            lines = response.strip().split("\n")
            summary = ""
            key_points = []

            for line in lines:
                if line.startswith("Summary:"):
                    summary = line.replace("Summary:", "").strip()
                elif line.startswith("- "):
                    key_points.append(line[2:].strip())

            topic.summary = summary
            topic.key_points = key_points[:5]
            topic.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        except Exception as e:
            logger.error(f"Error updating topic summary: {e}")

    # ==========================================
    # EPISODIC MEMORY - Keyword-based (EM)
    # ==========================================

    async def index_message_to_keywords(
        self,
        keywords: list[str],
        message_content: str,
        message_id: UUID | None = None,
    ) -> None:
        """Index a message by keywords."""
        for keyword in keywords[:20]:  # Limit keywords per message
            keyword = keyword.lower().strip()
            if len(keyword) < 3:
                continue

            # Get or create keyword index
            result = await self.db.execute(
                select(MemoryKeywordIndex).where(
                    and_(
                        MemoryKeywordIndex.session_id == self.session_id,
                        MemoryKeywordIndex.keyword == keyword,
                    )
                )
            )
            index = result.scalar_one_or_none()

            if index:
                index.occurrence_count += 1
                if message_id:
                    msg_ids = index.message_ids or []
                    msg_ids.append(message_id)
                    index.message_ids = msg_ids[-50:]  # Keep last 50
            else:
                index = MemoryKeywordIndex(
                    id=uuid4(),
                    session_id=self.session_id,
                    keyword=keyword,
                    occurrence_count=1,
                    message_ids=[message_id] if message_id else [],
                )
                self.db.add(index)

    async def search_by_keyword(
        self,
        keyword: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search messages by keyword."""
        from src.db.models import ChatMessage

        keyword = keyword.lower().strip()

        result = await self.db.execute(
            select(MemoryKeywordIndex).where(
                and_(
                    MemoryKeywordIndex.session_id == self.session_id,
                    MemoryKeywordIndex.keyword == keyword,
                )
            )
        )
        index = result.scalar_one_or_none()

        if not index or not index.message_ids:
            return []

        # Get messages
        msg_result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.id.in_(index.message_ids[-limit:]))
            .order_by(ChatMessage.timestamp.desc())
        )

        messages = []
        for msg in msg_result.scalars().all():
            messages.append({
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            })

        return messages

    async def get_top_keywords(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get most frequent keywords."""
        result = await self.db.execute(
            select(MemoryKeywordIndex)
            .where(MemoryKeywordIndex.session_id == self.session_id)
            .order_by(MemoryKeywordIndex.occurrence_count.desc())
            .limit(limit)
        )

        keywords = []
        for kw in result.scalars().all():
            keywords.append({
                "keyword": kw.keyword,
                "count": kw.occurrence_count,
                "message_count": len(kw.message_ids or []),
            })

        return keywords

    # ==========================================
    # UPDATE FROM INTERACTION
    # ==========================================

    async def update_from_interaction(
        self,
        user_message: str,
        assistant_response: str,
    ) -> None:
        """Update persona memory from an interaction."""
        from src.core.claude import claude_client

        # Sanitize user inputs to prevent prompt injection
        sanitized_user_msg = sanitize_user_input(user_message, max_length=500)
        sanitized_assistant_resp = sanitize_user_input(assistant_response, max_length=500)

        # Extract potential persona updates
        prompt = f"""Analyze this interaction for user profile updates:

User: {sanitized_user_msg}
Assistant: {sanitized_assistant_resp}

What can we learn about the user? Return JSON:
{{
    "attributes": ["list of new facts about user (preferences, habits, demographics)"],
    "event": "significant event mentioned (or null)",
    "event_time": "when event occurred (or null)"
}}

Return {{"attributes": [], "event": null}} if nothing to learn."""

        try:
            response = await claude_client.complete(
                prompt=prompt,
                system="Extract user profile information. Return valid JSON only.",
            )

            import json
            data = json.loads(response)

            # Add attributes
            for attr in data.get("attributes", [])[:3]:
                if attr and len(attr) > 5:
                    await self.add_persona_attribute(attr)

            # Add event
            event = data.get("event")
            if event and len(event) > 5:
                event_time = None
                if data.get("event_time"):
                    try:
                        event_time = datetime.fromisoformat(data["event_time"])
                    except ValueError:
                        pass
                await self.add_persona_event(event, event_time)

        except Exception as e:
            logger.debug(f"Could not extract persona updates: {e}")
