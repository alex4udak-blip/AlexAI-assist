"""Smart memory service for persistent AI context."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.claude import claude_client
from src.db.models import (
    Agent,
    ChatMessage,
    Event,
    MemoryInsight,
    MemorySummary,
    UserMemory,
)

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing AI memory across sessions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build_context(self, session_id: str) -> dict[str, str]:
        """Build full context for Claude from all memory layers."""
        return {
            "user_profile": await self.get_user_profile(session_id),
            "recent_summary": await self.get_recent_summary(session_id),
            "active_goals": await self.get_active_goals(session_id),
            "agent_status": await self.get_agent_status(),
            "recent_insights": await self.get_recent_insights(session_id, limit=5),
            "activity_context": await self.get_activity_context(),
        }

    async def get_user_profile(self, session_id: str) -> str:
        """Get user profile as formatted text."""
        query = (
            select(UserMemory)
            .where(UserMemory.session_id == session_id)
            .order_by(UserMemory.confidence.desc(), UserMemory.last_referenced.desc())
            .limit(20)
        )
        result = await self.db.execute(query)
        memories = result.scalars().all()

        if not memories:
            return "No user profile data yet."

        # Group by category
        by_category: dict[str, list[str]] = {}
        for mem in memories:
            cat = mem.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f"- {mem.key}: {mem.value}")

        lines = []
        for cat, items in by_category.items():
            lines.append(f"### {cat.title()}")
            lines.extend(items)
            lines.append("")

        return "\n".join(lines)

    async def get_recent_summary(self, session_id: str) -> str:
        """Get most recent daily/weekly summary."""
        query = (
            select(MemorySummary)
            .where(MemorySummary.session_id == session_id)
            .order_by(MemorySummary.period_end.desc())
            .limit(2)
        )
        result = await self.db.execute(query)
        summaries = result.scalars().all()

        if not summaries:
            return "No activity summaries yet."

        lines = []
        for summary in summaries:
            lines.append(f"**{summary.period_type.title()} Summary ({summary.period_start.strftime('%Y-%m-%d')}):**")
            lines.append(summary.summary)
            if summary.metrics:
                metrics = summary.metrics
                if "productivity" in metrics:
                    lines.append(f"- Productivity: {metrics['productivity']}%")
                if "focus_time" in metrics:
                    lines.append(f"- Focus time: {metrics['focus_time']} min")
            lines.append("")

        return "\n".join(lines)

    async def get_active_goals(self, session_id: str) -> str:
        """Get user's active goals from memory."""
        query = (
            select(UserMemory)
            .where(
                UserMemory.session_id == session_id,
                UserMemory.category == "goal",
            )
            .order_by(UserMemory.created_at.desc())
            .limit(5)
        )
        result = await self.db.execute(query)
        goals = result.scalars().all()

        if not goals:
            return "No active goals set."

        lines = ["Current goals:"]
        for goal in goals:
            lines.append(f"- {goal.key}: {goal.value}")

        return "\n".join(lines)

    async def get_agent_status(self) -> str:
        """Get status of all agents."""
        query = select(Agent).order_by(Agent.updated_at.desc()).limit(10)
        result = await self.db.execute(query)
        agents = result.scalars().all()

        if not agents:
            return "No agents created yet."

        lines = ["Active agents:"]
        for agent in agents:
            status_emoji = "active" if agent.status == "active" else "inactive"
            lines.append(
                f"- {agent.name} [{status_emoji}]: {agent.run_count} runs, "
                f"{agent.success_count} successes"
            )
            if agent.last_error:
                lines.append(f"  Last error: {agent.last_error[:100]}")

        return "\n".join(lines)

    async def get_recent_insights(self, session_id: str, limit: int = 5) -> str:
        """Get recent AI-generated insights."""
        query = (
            select(MemoryInsight)
            .where(MemoryInsight.session_id == session_id)
            .order_by(MemoryInsight.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        insights = result.scalars().all()

        if not insights:
            return "No insights generated yet."

        lines = ["Recent insights:"]
        for insight in insights:
            title = insight.title or insight.insight_type
            lines.append(f"- [{insight.insight_type}] {title}")
            if insight.content:
                lines.append(f"  {insight.content[:200]}")

        return "\n".join(lines)

    async def get_activity_context(self) -> str:
        """Get current activity context from recent events."""
        now = datetime.utcnow()
        start = now - timedelta(hours=24)

        # Get event counts
        count_query = select(func.count(Event.id)).where(Event.timestamp >= start)
        result = await self.db.execute(count_query)
        total_events = result.scalar() or 0

        # Get top apps
        apps_query = (
            select(Event.app_name, func.count(Event.id).label("count"))
            .where(Event.timestamp >= start, Event.app_name.isnot(None))
            .group_by(Event.app_name)
            .order_by(func.count(Event.id).desc())
            .limit(5)
        )
        result = await self.db.execute(apps_query)
        top_apps = result.all()

        # Get category breakdown
        cat_query = (
            select(Event.category, func.count(Event.id).label("count"))
            .where(Event.timestamp >= start, Event.category.isnot(None))
            .group_by(Event.category)
            .order_by(func.count(Event.id).desc())
        )
        result = await self.db.execute(cat_query)
        categories = result.all()

        lines = [
            f"Today's activity: {total_events} events",
            f"Top apps: {', '.join([f'{app[0]} ({app[1]})' for app in top_apps])}",
            f"Categories: {', '.join([f'{cat[0]}: {cat[1]}' for cat in categories])}",
        ]

        return "\n".join(lines)

    async def extract_facts_from_chat(
        self, session_id: str, user_message: str, assistant_response: str
    ) -> None:
        """Use Claude to extract facts from conversation and save them."""
        try:
            prompt = f"""Analyze this conversation and extract any facts about the user.
Return JSON array with objects containing: category, key, value, confidence (0-1)

Categories: preference, fact, goal, habit, interest

User: {user_message}
Assistant: {assistant_response}

Only extract clear facts. Return empty array [] if no facts found.
Example: [{{"category": "preference", "key": "favorite_language", "value": "Python", "confidence": 0.9}}]

JSON:"""

            result = await claude_client.complete(
                prompt=prompt,
                system="Extract facts from conversations. Return only valid JSON array.",
                max_tokens=500,
            )

            # Parse JSON from response
            result = result.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[1].rsplit("```", 1)[0]

            facts = json.loads(result)

            for fact in facts:
                if all(k in fact for k in ["category", "key", "value"]):
                    await self.save_fact(
                        session_id=session_id,
                        category=fact["category"],
                        key=fact["key"],
                        value=fact["value"],
                        confidence=fact.get("confidence", 0.8),
                        source="chat",
                    )

            await self.db.commit()
            logger.info(f"Extracted {len(facts)} facts from chat")

        except json.JSONDecodeError:
            logger.debug("No valid JSON facts extracted from chat")
        except Exception as e:
            logger.error(f"Error extracting facts: {e}")

    async def save_fact(
        self,
        session_id: str,
        category: str,
        key: str,
        value: str,
        confidence: float = 1.0,
        source: str | None = None,
    ) -> UserMemory:
        """Save or update a fact in user memory."""
        # Check if fact exists
        query = select(UserMemory).where(
            UserMemory.session_id == session_id,
            UserMemory.key == key,
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing fact
            existing.value = value
            existing.confidence = max(existing.confidence, confidence)
            existing.last_referenced = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            return existing
        else:
            # Create new fact
            memory = UserMemory(
                id=uuid4(),
                session_id=session_id,
                category=category,
                key=key,
                value=value,
                confidence=confidence,
                source=source,
                created_at=datetime.utcnow(),
            )
            self.db.add(memory)
            return memory

    async def create_daily_summary(self, session_id: str, date: datetime) -> MemorySummary | None:
        """Create summary of day's activity and chats."""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        # Check if summary already exists
        existing_query = select(MemorySummary).where(
            MemorySummary.session_id == session_id,
            MemorySummary.period_type == "daily",
            MemorySummary.period_start == start,
        )
        result = await self.db.execute(existing_query)
        if result.scalar_one_or_none():
            return None  # Already exists

        # Get day's events
        events_query = (
            select(Event)
            .where(Event.timestamp >= start, Event.timestamp < end)
            .order_by(Event.timestamp)
        )
        result = await self.db.execute(events_query)
        events = result.scalars().all()

        # Get day's chats
        chats_query = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.timestamp >= start,
                ChatMessage.timestamp < end,
            )
            .order_by(ChatMessage.timestamp)
        )
        result = await self.db.execute(chats_query)
        chats = result.scalars().all()

        if not events and not chats:
            return None  # Nothing to summarize

        # Calculate metrics
        total_events = len(events)
        app_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}

        for event in events:
            if event.app_name:
                app_counts[event.app_name] = app_counts.get(event.app_name, 0) + 1
            if event.category:
                category_counts[event.category] = (
                    category_counts.get(event.category, 0) + 1
                )

        productive = sum(
            category_counts.get(c, 0) for c in ["coding", "writing", "design", "research"]
        )
        productivity = int((productive / total_events * 100) if total_events else 0)

        metrics = {
            "total_events": total_events,
            "productivity": productivity,
            "top_apps": sorted(app_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "categories": category_counts,
            "chat_messages": len(chats),
        }

        # Build summary text
        top_apps_str = ", ".join([f"{app[0]} ({app[1]})" for app in metrics["top_apps"]])
        summary_lines = [
            f"Activity: {total_events} events tracked",
            f"Top apps: {top_apps_str}",
            f"Productivity score: {productivity}%",
            f"Chat interactions: {len(chats)} messages",
        ]

        summary = MemorySummary(
            id=uuid4(),
            session_id=session_id,
            period_type="daily",
            period_start=start,
            period_end=end,
            summary="\n".join(summary_lines),
            metrics=metrics,
            created_at=datetime.utcnow(),
        )
        self.db.add(summary)

        return summary
