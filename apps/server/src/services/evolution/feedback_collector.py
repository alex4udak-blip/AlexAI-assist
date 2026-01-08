"""Feedback collector service for evolution system.

This module collects feedback from multiple sources:
1. Explicit user feedback (thumbs up/down, comments)
2. Implicit signals (edits, retries, abandonment)
3. System metrics (errors, latency, success rates)
4. LLM-as-judge evaluations
"""

import logging
import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Agent, AgentLog, ChatMessage

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Collects feedback from various sources for system evolution."""

    # Sentiment detection phrases
    POSITIVE_PHRASES = [
        "thanks",
        "thank you",
        "perfect",
        "exactly",
        "great",
        "awesome",
        "excellent",
        "спасибо",
        "отлично",
        "круто",
        "супер",
        "прекрасно",
    ]

    NEGATIVE_PHRASES = [
        "wrong",
        "no",
        "not what",
        "try again",
        "incorrect",
        "error",
        "нет",
        "не то",
        "неправильно",
        "ошибка",
        "не так",
        "плохо",
    ]

    QUALITY_PHRASES = [
        "too long",
        "too short",
        "confusing",
        "unclear",
        "verbose",
        "длинно",
        "коротко",
        "непонятно",
        "слишком",
        "мало",
    ]

    def __init__(self, db: AsyncSession) -> None:
        """Initialize feedback collector.

        Args:
            db: Database session for querying data
        """
        self.db = db

    async def collect_since(
        self,
        since: datetime,
    ) -> dict[str, Any]:
        """Collect all feedback since timestamp.

        Args:
            since: Timestamp to collect feedback from

        Returns:
            Dictionary with feedback from all sources:
            - chat_feedback: Feedback extracted from chat messages
            - agent_feedback: Feedback from agent executions
            - system_feedback: System health metrics
        """
        logger.info(f"Collecting feedback since {since}")

        chat_feedback = await self._collect_chat_feedback(since)
        agent_feedback = await self._collect_agent_feedback(since)
        system_feedback = await self._collect_system_feedback(since)

        total_feedback_items = (
            len(chat_feedback.get("positive", []))
            + len(chat_feedback.get("negative", []))
            + len(chat_feedback.get("quality_issues", []))
            + len(agent_feedback.get("errors", []))
        )

        logger.info(f"Collected {total_feedback_items} feedback items")

        return {
            "chat_feedback": chat_feedback,
            "agent_feedback": agent_feedback,
            "system_feedback": system_feedback,
            "collected_at": datetime.utcnow(),
            "period_start": since,
            "total_items": total_feedback_items,
        }

    async def _collect_chat_feedback(
        self,
        since: datetime,
    ) -> dict[str, Any]:
        """Extract feedback from chat messages.

        Analyzes chat messages for:
        - Positive signals (thanks, perfect, etc.)
        - Negative signals (wrong, no, etc.)
        - Quality issues (too long, confusing, etc.)

        Args:
            since: Timestamp to collect messages from

        Returns:
            Dictionary with categorized feedback:
            - positive: List of positive feedback items
            - negative: List of negative feedback items
            - quality_issues: List of quality concerns
            - total_messages: Total messages analyzed
        """
        query = (
            select(ChatMessage)
            .where(
                ChatMessage.timestamp >= since,
                ChatMessage.role == "user",
            )
            .order_by(ChatMessage.timestamp.desc())
        )

        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        positive_feedback: list[dict[str, Any]] = []
        negative_feedback: list[dict[str, Any]] = []
        quality_issues: list[dict[str, Any]] = []

        for msg in messages:
            content_lower = msg.content.lower()

            # Check for positive signals
            positive_matches = self._find_phrase_matches(
                content_lower, self.POSITIVE_PHRASES
            )
            if positive_matches:
                positive_feedback.append(
                    {
                        "message_id": str(msg.id),
                        "session_id": msg.session_id,
                        "content": msg.content,
                        "timestamp": msg.timestamp,
                        "matched_phrases": positive_matches,
                        "type": "implicit_positive",
                    }
                )

            # Check for negative signals
            negative_matches = self._find_phrase_matches(
                content_lower, self.NEGATIVE_PHRASES
            )
            if negative_matches:
                negative_feedback.append(
                    {
                        "message_id": str(msg.id),
                        "session_id": msg.session_id,
                        "content": msg.content,
                        "timestamp": msg.timestamp,
                        "matched_phrases": negative_matches,
                        "type": "implicit_negative",
                    }
                )

            # Check for quality issues
            quality_matches = self._find_phrase_matches(
                content_lower, self.QUALITY_PHRASES
            )
            if quality_matches:
                quality_issues.append(
                    {
                        "message_id": str(msg.id),
                        "session_id": msg.session_id,
                        "content": msg.content,
                        "timestamp": msg.timestamp,
                        "matched_phrases": quality_matches,
                        "type": "quality_concern",
                    }
                )

        logger.info(
            f"Chat feedback: {len(positive_feedback)} positive, "
            f"{len(negative_feedback)} negative, "
            f"{len(quality_issues)} quality issues from {len(messages)} messages"
        )

        return {
            "positive": positive_feedback,
            "negative": negative_feedback,
            "quality_issues": quality_issues,
            "total_messages": len(messages),
        }

    async def _collect_agent_feedback(
        self,
        since: datetime,
    ) -> dict[str, Any]:
        """Collect feedback from agent executions.

        Analyzes agent logs for:
        - Errors and failures
        - Success rates
        - Performance issues

        Args:
            since: Timestamp to collect logs from

        Returns:
            Dictionary with agent feedback:
            - errors: List of error logs
            - warnings: List of warning logs
            - success_rate: Overall success rate
            - total_runs: Total agent runs analyzed
        """
        # Get all agents updated since timestamp
        agents_query = select(Agent).where(Agent.updated_at >= since)
        agents_result = await self.db.execute(agents_query)
        agents = list(agents_result.scalars().all())

        # Get error and warning logs
        logs_query = (
            select(AgentLog)
            .where(
                AgentLog.created_at >= since,
                AgentLog.level.in_(["error", "warning"]),
            )
            .order_by(AgentLog.created_at.desc())
        )
        logs_result = await self.db.execute(logs_query)
        logs = list(logs_result.scalars().all())

        errors: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        for log in logs:
            log_data = {
                "log_id": str(log.id),
                "agent_id": str(log.agent_id),
                "message": log.message,
                "timestamp": log.created_at,
                "data": log.data or {},
            }

            if log.level == "error":
                errors.append(log_data)
            elif log.level == "warning":
                warnings.append(log_data)

        # Calculate success rate
        total_runs = sum(agent.run_count for agent in agents)
        total_successes = sum(agent.success_count for agent in agents)
        success_rate = (
            (total_successes / total_runs * 100) if total_runs > 0 else 0.0
        )

        # Identify poorly performing agents
        poor_performers: list[dict[str, Any]] = []
        for agent in agents:
            if agent.run_count >= 3:  # Only consider agents with enough runs
                agent_success_rate = (
                    (agent.success_count / agent.run_count * 100)
                    if agent.run_count > 0
                    else 0.0
                )
                if agent_success_rate < 50:  # Less than 50% success rate
                    poor_performers.append(
                        {
                            "agent_id": str(agent.id),
                            "name": agent.name,
                            "success_rate": agent_success_rate,
                            "run_count": agent.run_count,
                            "success_count": agent.success_count,
                            "last_error": agent.last_error,
                        }
                    )

        logger.info(
            f"Agent feedback: {len(errors)} errors, {len(warnings)} warnings, "
            f"{len(poor_performers)} poor performers, success rate: {success_rate:.1f}%"
        )

        return {
            "errors": errors,
            "warnings": warnings,
            "poor_performers": poor_performers,
            "success_rate": success_rate,
            "total_runs": total_runs,
            "total_agents": len(agents),
        }

    async def _collect_system_feedback(
        self,
        since: datetime,
    ) -> dict[str, Any]:
        """Collect system health metrics.

        Args:
            since: Timestamp to collect metrics from

        Returns:
            Dictionary with system metrics:
            - chat_volume: Number of chat messages
            - agent_activity: Number of agent runs
            - error_rate: Overall error rate
            - period: Time period analyzed
        """
        # Chat message volume
        chat_query = select(func.count(ChatMessage.id)).where(
            ChatMessage.timestamp >= since
        )
        chat_result = await self.db.execute(chat_query)
        chat_volume = chat_result.scalar() or 0

        # Agent activity
        agent_query = select(Agent).where(Agent.last_run_at >= since)
        agent_result = await self.db.execute(agent_query)
        active_agents = list(agent_result.scalars().all())

        total_agent_runs = sum(
            agent.run_count for agent in active_agents if agent.last_run_at and agent.last_run_at >= since
        )
        total_agent_errors = sum(
            agent.error_count for agent in active_agents if agent.last_run_at and agent.last_run_at >= since
        )

        error_rate = (
            (total_agent_errors / total_agent_runs * 100)
            if total_agent_runs > 0
            else 0.0
        )

        # Calculate time period
        period_hours = (datetime.utcnow() - since).total_seconds() / 3600

        logger.info(
            f"System metrics: {chat_volume} messages, "
            f"{total_agent_runs} agent runs, {error_rate:.1f}% error rate "
            f"over {period_hours:.1f} hours"
        )

        return {
            "chat_volume": chat_volume,
            "agent_activity": {
                "total_runs": total_agent_runs,
                "total_errors": total_agent_errors,
                "active_agents": len(active_agents),
            },
            "error_rate": error_rate,
            "period_hours": period_hours,
        }

    async def add_explicit_feedback(
        self,
        feedback_type: str,
        content: str,
        category: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add explicit user feedback.

        This allows users to directly provide feedback through UI controls
        like thumbs up/down, star ratings, or comment forms.

        Args:
            feedback_type: Type of feedback (e.g., "thumbs_up", "thumbs_down", "rating", "comment")
            content: Feedback content or value
            category: Optional category (e.g., "response_quality", "accuracy", "helpfulness")
            context: Optional context (e.g., message_id, session_id, agent_id)

        Returns:
            Dictionary with feedback record:
            - id: Feedback ID
            - type: Feedback type
            - content: Feedback content
            - category: Feedback category
            - context: Associated context
            - timestamp: When feedback was added
        """
        feedback_record = {
            "id": str(uuid4()),
            "type": feedback_type,
            "content": content,
            "category": category,
            "context": context or {},
            "timestamp": datetime.utcnow(),
        }

        logger.info(
            f"Explicit feedback added: {feedback_type} - {category or 'uncategorized'}"
        )

        # In a real implementation, this would be stored in a dedicated feedback table
        # For now, we return the structured feedback record
        # TODO: Create and use a Feedback model/table for persistent storage

        return feedback_record

    def _find_phrase_matches(
        self, text: str, phrases: list[str]
    ) -> list[str]:
        """Find matching phrases in text.

        Args:
            text: Text to search (should be lowercased)
            phrases: List of phrases to look for

        Returns:
            List of matched phrases
        """
        matches = []
        for phrase in phrases:
            # Use word boundaries to avoid partial matches
            pattern = r"\b" + re.escape(phrase.lower()) + r"\b"
            if re.search(pattern, text):
                matches.append(phrase)
        return matches
