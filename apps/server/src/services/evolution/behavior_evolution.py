"""Behavior Evolution Service - learns user interaction preferences over time."""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.claude import claude_client
from src.db.models.chat import ChatMessage

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Get current UTC time as naive datetime for database compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


class BehaviorEvolution:
    """
    Learns and adapts assistant behavior based on user interactions.

    Tracks preferences like verbosity, formality, proactivity level,
    and adjusts system prompts accordingly.
    """

    # Default behavior parameters (0.0 - 1.0 scale)
    DEFAULT_BEHAVIOR: dict[str, float] = {
        "verbosity": 0.5,  # 0=concise, 1=detailed
        "ask_threshold": 0.5,  # 0=just do it, 1=always ask
        "formality": 0.5,  # 0=casual, 1=formal
        "proactivity": 0.5,  # 0=reactive, 1=proactive
        "emoji_usage": 0.0,  # 0=none, 1=frequent (per CLAUDE.md: no emojis in UI)
        "code_detail": 0.6,  # 0=minimal, 1=verbose with comments
        "russian_english_mix": 0.3,  # 0=english only, 1=more russian
    }

    # Signals for detecting user preferences from feedback
    positive_signals: list[str] = [
        "спасибо",
        "отлично",
        "хорошо",
        "perfect",
        "thanks",
        "great",
        "good job",
        "exactly",
        "именно",
        "правильно",
        "да, так",
        "yes",
    ]

    negative_signals: list[str] = [
        "слишком",
        "too much",
        "not what",
        "нет",
        "no",
        "wrong",
        "не то",
        "shorter",
        "короче",
        "подробнее",
        "more detail",
        "less detail",
        "stop",
        "don't",
        "не надо",
    ]

    def __init__(self, db: AsyncSession, session_id: str = "default") -> None:
        """Initialize behavior evolution service."""
        self.db = db
        self.session_id = session_id
        self.behavior: dict[str, float] = self.DEFAULT_BEHAVIOR.copy()
        self.history: list[dict[str, Any]] = []
        self.evolution_count = 0

    async def evolve(self, issues: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Main evolution method - analyze interactions and adjust behavior.

        Args:
            issues: List of issues/patterns detected from recent interactions

        Returns:
            Evolution summary with changes made
        """
        logger.info(f"Starting behavior evolution for session {self.session_id}")

        # Save current state for potential rollback
        await self._save_behavior_history()

        # Analyze recent chat patterns
        chat_analysis = await self._analyze_recent_chats()

        # Get LLM-based insights
        insights = await self._get_behavior_insights(issues, chat_analysis)

        changes: list[str] = []

        # Apply insights
        for insight in insights:
            change = await self._apply_insight(insight)
            if change:
                changes.append(change)

        # Detect simple patterns from user messages
        if chat_analysis.get("negative_feedback_count", 0) > 2:
            # User expressed dissatisfaction, reduce confidence in current behavior
            self._adjust_param("ask_threshold", 0.1)
            changes.append("Increased ask_threshold due to negative feedback")

        if chat_analysis.get("brevity_requests", 0) > 0:
            self._adjust_param("verbosity", -0.15)
            changes.append("Reduced verbosity based on user requests")

        if chat_analysis.get("detail_requests", 0) > 0:
            self._adjust_param("verbosity", 0.15)
            changes.append("Increased verbosity based on user requests")

        self.evolution_count += 1

        result = {
            "session_id": self.session_id,
            "evolution_count": self.evolution_count,
            "current_behavior": self.behavior.copy(),
            "changes": changes,
            "timestamp": _utc_now().isoformat(),
        }

        logger.info(f"Evolution complete: {len(changes)} changes applied")
        return result

    async def _analyze_recent_chats(self, days: int = 7, limit: int = 50) -> dict[str, Any]:
        """
        Analyze recent chat messages to infer user preferences.

        Returns:
            Analysis dict with detected patterns
        """
        cutoff_date = _utc_now() - timedelta(days=days)

        query = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == self.session_id,
                ChatMessage.timestamp >= cutoff_date,
            )
            .order_by(ChatMessage.timestamp.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        messages = result.scalars().all()

        analysis: dict[str, Any] = {
            "total_messages": len(messages),
            "user_messages": 0,
            "assistant_messages": 0,
            "avg_user_length": 0,
            "avg_assistant_length": 0,
            "positive_feedback_count": 0,
            "negative_feedback_count": 0,
            "brevity_requests": 0,
            "detail_requests": 0,
            "russian_usage": 0,
            "english_usage": 0,
        }

        if not messages:
            return analysis

        user_lengths: list[int] = []
        assistant_lengths: list[int] = []

        for msg in messages:
            content_lower = msg.content.lower()

            if msg.role == "user":
                analysis["user_messages"] += 1
                user_lengths.append(len(msg.content))

                # Detect feedback signals
                if any(signal in content_lower for signal in self.positive_signals):
                    analysis["positive_feedback_count"] += 1

                if any(signal in content_lower for signal in self.negative_signals):
                    analysis["negative_feedback_count"] += 1

                # Detect verbosity preferences
                if any(word in content_lower for word in ["shorter", "brief", "короче", "кратко"]):
                    analysis["brevity_requests"] += 1

                if any(word in content_lower for word in ["detail", "more", "подробнее", "больше"]):
                    analysis["detail_requests"] += 1

                # Detect language usage (simple heuristic: cyrillic characters)
                if any(ord(char) >= 0x0400 and ord(char) <= 0x04FF for char in msg.content):
                    analysis["russian_usage"] += 1
                else:
                    analysis["english_usage"] += 1

            elif msg.role == "assistant":
                analysis["assistant_messages"] += 1
                assistant_lengths.append(len(msg.content))

        # Calculate averages
        if user_lengths:
            analysis["avg_user_length"] = sum(user_lengths) / len(user_lengths)

        if assistant_lengths:
            analysis["avg_assistant_length"] = sum(assistant_lengths) / len(assistant_lengths)

        return analysis

    async def _get_behavior_insights(
        self,
        issues: list[dict[str, Any]],
        chat_analysis: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Use LLM to analyze patterns and suggest behavior adjustments.

        Args:
            issues: Detected issues from recent interactions
            chat_analysis: Statistical analysis of chat patterns

        Returns:
            List of insights with suggested parameter adjustments
        """
        try:
            prompt = f"""Analyze this user interaction data and suggest behavior parameter adjustments.

Current Behavior Parameters:
{json.dumps(self.behavior, indent=2)}

Chat Analysis (last 7 days):
{json.dumps(chat_analysis, indent=2)}

Detected Issues:
{json.dumps(issues, indent=2)}

Based on this data, suggest 0-3 specific parameter adjustments.
Consider:
- User feedback patterns (positive/negative)
- Verbosity preferences (brevity vs detail requests)
- Language preference (Russian/English ratio)
- Engagement patterns

Respond with JSON array of insights:
[
  {{
    "parameter": "verbosity",
    "adjustment": -0.1,
    "reasoning": "User requested shorter responses 3 times"
  }}
]

Only suggest changes if there's clear evidence. Return empty array [] if no changes needed.
"""

            system = """You are a behavior analysis expert for an AI assistant.
Analyze user interaction patterns and suggest parameter adjustments on a 0.0-1.0 scale.
Be conservative - only suggest changes with strong evidence.
Always respond with valid JSON."""

            response = await claude_client.complete(
                prompt=prompt,
                system=system,
                max_tokens=2048,
            )

            # Parse JSON response
            insights = json.loads(response.strip())

            if not isinstance(insights, list):
                logger.warning(f"LLM returned non-list response: {insights}")
                return []

            logger.info(f"LLM suggested {len(insights)} behavior adjustments")
            return insights

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM insights: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting LLM insights: {e}")
            return []

    def _adjust_param(self, param: str, delta: float) -> None:
        """
        Adjust a behavior parameter by delta, clamping to [0.0, 1.0].

        Args:
            param: Parameter name
            delta: Amount to adjust (can be negative)
        """
        if param not in self.behavior:
            logger.warning(f"Unknown parameter: {param}")
            return

        old_value = self.behavior[param]
        new_value = max(0.0, min(1.0, old_value + delta))
        self.behavior[param] = new_value

        logger.debug(f"Adjusted {param}: {old_value:.2f} -> {new_value:.2f} (delta: {delta:+.2f})")

    async def _apply_insight(self, insight: dict[str, Any]) -> str | None:
        """
        Apply an LLM-generated insight to behavior parameters.

        Args:
            insight: Dict with parameter, adjustment, and reasoning

        Returns:
            Description of change made, or None if invalid
        """
        param = insight.get("parameter")
        adjustment = insight.get("adjustment")
        reasoning = insight.get("reasoning", "No reason provided")

        if not param or adjustment is None:
            logger.warning(f"Invalid insight format: {insight}")
            return None

        if param not in self.behavior:
            logger.warning(f"Unknown parameter in insight: {param}")
            return None

        # Validate adjustment magnitude (safety check)
        if abs(adjustment) > 0.3:
            logger.warning(f"Large adjustment rejected: {adjustment} for {param}")
            return None

        old_value = self.behavior[param]
        self._adjust_param(param, adjustment)
        new_value = self.behavior[param]

        change_desc = f"Adjusted {param} from {old_value:.2f} to {new_value:.2f}: {reasoning}"
        logger.info(change_desc)

        return change_desc

    async def _save_behavior_history(self) -> None:
        """Save current behavior state to history for potential rollback."""
        snapshot = {
            "behavior": self.behavior.copy(),
            "timestamp": _utc_now().isoformat(),
            "evolution_count": self.evolution_count,
        }

        self.history.append(snapshot)

        # Keep only last 10 snapshots to prevent unbounded growth
        if len(self.history) > 10:
            self.history = self.history[-10:]

        logger.debug(f"Saved behavior snapshot (history size: {len(self.history)})")

    async def rollback(self, steps: int = 1) -> dict[str, Any]:
        """
        Rollback behavior to a previous state.

        Args:
            steps: Number of evolution steps to roll back

        Returns:
            Result dict with rollback status
        """
        if not self.history:
            return {
                "success": False,
                "error": "No history available for rollback",
            }

        if steps > len(self.history):
            steps = len(self.history)

        # Rollback to previous state
        target_snapshot = self.history[-(steps + 1)] if steps < len(self.history) else self.history[0]

        old_behavior = self.behavior.copy()
        self.behavior = target_snapshot["behavior"].copy()
        self.evolution_count = target_snapshot["evolution_count"]

        # Remove rolled-back snapshots
        self.history = self.history[:-(steps)]

        logger.info(f"Rolled back {steps} evolution step(s)")

        return {
            "success": True,
            "steps_rolled_back": steps,
            "old_behavior": old_behavior,
            "current_behavior": self.behavior.copy(),
        }

    def get_behavior_prompt_modifier(self) -> str:
        """
        Generate a system prompt modifier based on current behavior parameters.

        Returns:
            String to append to system prompt
        """
        modifiers: list[str] = []

        # Verbosity
        if self.behavior["verbosity"] < 0.3:
            modifiers.append("Provide concise, brief responses. Avoid unnecessary details.")
        elif self.behavior["verbosity"] > 0.7:
            modifiers.append("Provide detailed, comprehensive responses with thorough explanations.")

        # Ask threshold
        if self.behavior["ask_threshold"] < 0.3:
            modifiers.append("Be proactive - take reasonable actions without always asking for confirmation.")
        elif self.behavior["ask_threshold"] > 0.7:
            modifiers.append("Always ask for clarification and confirmation before taking significant actions.")

        # Formality
        if self.behavior["formality"] < 0.3:
            modifiers.append("Use a casual, friendly tone in responses.")
        elif self.behavior["formality"] > 0.7:
            modifiers.append("Maintain a professional, formal tone in all interactions.")

        # Proactivity
        if self.behavior["proactivity"] < 0.3:
            modifiers.append("Focus on answering the direct question without suggesting additional actions.")
        elif self.behavior["proactivity"] > 0.7:
            modifiers.append("Proactively suggest related improvements and next steps.")

        # Code detail
        if self.behavior["code_detail"] < 0.3:
            modifiers.append("Keep code minimal without extensive comments.")
        elif self.behavior["code_detail"] > 0.7:
            modifiers.append("Include detailed comments and explanations in code.")

        # Language preference
        if self.behavior["russian_english_mix"] > 0.6:
            modifiers.append("User prefers Russian language - respond primarily in Russian when appropriate.")
        elif self.behavior["russian_english_mix"] < 0.2:
            modifiers.append("User prefers English - keep responses in English.")

        # Per CLAUDE.md: no emojis in interface
        # emoji_usage is kept for potential future use but currently disabled
        modifiers.append("NEVER use emojis in responses or interface elements.")

        if not modifiers:
            return ""

        return "\n\nBehavior Adaptations:\n" + "\n".join(f"- {mod}" for mod in modifiers)
