"""Agent suggester service for pattern-based automation suggestions."""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.db.models import Event
from src.services.ai_router import AIRouter, TaskComplexity

logger = get_logger(__name__)


def utc_now() -> datetime:
    """Get current UTC time as naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AgentSuggester:
    """Analyze patterns and suggest automation agents."""

    # Default thresholds for pattern detection (more aggressive for faster agent creation)
    DEFAULT_MIN_SEQUENCE_OCCURRENCES = 2
    DEFAULT_MIN_TIME_PATTERN_OCCURRENCES = 3
    DEFAULT_MIN_SWITCH_FREQUENCY = 5
    DEFAULT_LOOKBACK_DAYS = 3

    def __init__(self, ai_router: AIRouter):
        """Initialize with AI router for generating suggestions."""
        self.ai_router = ai_router

        # Load configurable thresholds from environment variables
        self.MIN_SEQUENCE_OCCURRENCES = int(
            os.getenv("AGENT_MIN_SEQUENCE_OCCURRENCES", self.DEFAULT_MIN_SEQUENCE_OCCURRENCES)
        )
        self.MIN_TIME_PATTERN_OCCURRENCES = int(
            os.getenv("AGENT_MIN_TIME_PATTERN_OCCURRENCES", self.DEFAULT_MIN_TIME_PATTERN_OCCURRENCES)
        )
        self.MIN_SWITCH_FREQUENCY = int(
            os.getenv("AGENT_MIN_SWITCH_FREQUENCY", self.DEFAULT_MIN_SWITCH_FREQUENCY)
        )
        self.LOOKBACK_DAYS = int(
            os.getenv("AGENT_LOOKBACK_DAYS", self.DEFAULT_LOOKBACK_DAYS)
        )

        logger.info(
            "AgentSuggester initialized with thresholds",
            extra={
                "lookback_days": self.LOOKBACK_DAYS,
                "min_sequence_occurrences": self.MIN_SEQUENCE_OCCURRENCES,
                "min_time_pattern_occurrences": self.MIN_TIME_PATTERN_OCCURRENCES,
                "min_switch_frequency": self.MIN_SWITCH_FREQUENCY,
            },
        )

    async def analyze_and_suggest(
        self,
        user_id: str,
        db: AsyncSession,
        device_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Analyze user behavior and suggest automation agents."""
        # Fetch recent events
        end_date = utc_now()
        start_date = end_date - timedelta(days=self.LOOKBACK_DAYS)

        query = select(Event).where(
            and_(
                Event.timestamp >= start_date,
                Event.timestamp <= end_date,
            )
        )

        if device_id:
            query = query.where(Event.device_id == device_id)

        result = await db.execute(query.order_by(Event.timestamp))
        events = result.scalars().all()

        if len(events) < 10:
            logger.info(
                "Not enough events for pattern analysis",
                extra={"event_count": len(events)},
            )
            return None

        # Convert to dicts for analysis
        event_dicts = [
            {
                "id": str(event.id),
                "device_id": event.device_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "app_name": event.app_name,
                "window_title": event.window_title,
                "url": event.url,
                "category": event.category,
            }
            for event in events
        ]

        logger.info(
            "Analyzing patterns for agent suggestions",
            extra={
                "user_id": user_id,
                "event_count": len(event_dicts),
                "days": self.LOOKBACK_DAYS,
            },
        )

        # Find patterns
        patterns = self._find_patterns(event_dicts)

        if not patterns:
            logger.info("No significant patterns found")
            return None

        # Generate suggestion for most significant pattern
        suggestion = await self._generate_suggestion(patterns[0])

        if suggestion:
            logger.info(
                "Agent suggestion generated",
                extra={
                    "pattern_type": patterns[0]["type"],
                    "confidence": patterns[0]["confidence"],
                },
            )

        return suggestion

    def _find_patterns(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Find automation patterns in events."""
        patterns = []

        # Find app sequences
        app_sequences = self._find_app_sequences(events)
        for sequence, count in app_sequences.most_common(3):
            if count >= self.MIN_SEQUENCE_OCCURRENCES:
                patterns.append(
                    {
                        "type": "app_sequence",
                        "sequence": sequence,
                        "occurrences": count,
                        "confidence": min(count / 5, 1.0),  # More aggressive: 5 occurrences = 100% confidence
                        "data": {"apps": sequence},
                    }
                )

        # Find time patterns
        time_patterns = self._find_time_patterns(events)
        for pattern in time_patterns:
            if pattern["occurrences"] >= self.MIN_TIME_PATTERN_OCCURRENCES:
                patterns.append(pattern)

        # Find context switch patterns
        switch_patterns = self._find_switch_patterns(events)
        for pattern in switch_patterns:
            if pattern["frequency"] >= self.MIN_SWITCH_FREQUENCY:
                patterns.append(pattern)

        # Sort by confidence
        patterns.sort(key=lambda p: p.get("confidence", 0), reverse=True)

        logger.debug(
            "Patterns found",
            extra={"pattern_count": len(patterns)},
        )

        return patterns

    def _find_app_sequences(
        self,
        events: list[dict[str, Any]],
    ) -> Counter[tuple[str, ...]]:
        """Find common app sequences (e.g., Browser -> IDE -> Terminal)."""
        sequences = Counter()

        # Group events by day
        days = defaultdict(list)
        for event in events:
            if event["app_name"]:
                day = event["timestamp"].strftime("%Y-%m-%d")
                days[day].append(event["app_name"])

        # Find sequences within each day
        for day_events in days.values():
            if len(day_events) < 3:
                continue

            # Look for 3-app sequences
            for i in range(len(day_events) - 2):
                sequence = tuple(day_events[i : i + 3])
                # Filter out repeated apps
                if len(set(sequence)) == 3:
                    sequences[sequence] += 1

        return sequences

    def _find_time_patterns(
        self,
        events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Find time-based patterns (e.g., daily routines)."""
        patterns = []

        # Group by hour and app
        hourly_apps = defaultdict(lambda: defaultdict(int))
        for event in events:
            if event["app_name"]:
                hour = event["timestamp"].hour
                hourly_apps[hour][event["app_name"]] += 1

        # Find consistent hourly patterns
        for hour, apps in hourly_apps.items():
            for app, count in apps.items():
                if count >= self.MIN_TIME_PATTERN_OCCURRENCES:
                    # Calculate confidence based on consistency
                    days_active = len(
                        set(
                            e["timestamp"].strftime("%Y-%m-%d")
                            for e in events
                            if e["app_name"] == app
                            and e["timestamp"].hour == hour
                        )
                    )
                    confidence = min(days_active / 3, 1.0)  # More aggressive: 3 days = 100% confidence

                    patterns.append(
                        {
                            "type": "time_pattern",
                            "hour": hour,
                            "app": app,
                            "occurrences": count,
                            "days_active": days_active,
                            "confidence": confidence,
                            "data": {"hour": hour, "app": app},
                        }
                    )

        return patterns

    def _find_switch_patterns(
        self,
        events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Find frequent context switching patterns."""
        patterns = []

        # Count app switches
        switches = defaultdict(lambda: defaultdict(int))
        prev_app = None

        for event in events:
            app = event["app_name"]
            if app and prev_app and app != prev_app:
                switches[prev_app][app] += 1
            prev_app = app

        # Find frequent switches
        for from_app, to_apps in switches.items():
            for to_app, count in to_apps.items():
                if count >= self.MIN_SWITCH_FREQUENCY:
                    confidence = min(count / 10, 1.0)  # More aggressive: 10 switches = 100% confidence
                    patterns.append(
                        {
                            "type": "switch_pattern",
                            "from_app": from_app,
                            "to_app": to_app,
                            "frequency": count,
                            "confidence": confidence,
                            "data": {"from_app": from_app, "to_app": to_app},
                        }
                    )

        return patterns

    async def _generate_suggestion(
        self,
        pattern: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Generate automation suggestion using AI."""
        pattern_type = pattern["type"]
        confidence = pattern["confidence"]

        # Build context for AI
        if pattern_type == "app_sequence":
            context = f"""Pattern: User frequently uses these apps in sequence: {' → '.join(pattern['sequence'])}
Occurrences: {pattern['occurrences']}
Confidence: {confidence:.2%}"""
            prompt = """Based on this app usage pattern, suggest an automation agent that could help.

Consider:
- What task might this sequence accomplish?
- How could an agent streamline this workflow?
- What actions could be automated?

Respond in JSON format:
{
    "agent_name": "descriptive name",
    "description": "what the agent does",
    "trigger": "when it should activate",
    "actions": ["list", "of", "actions"],
    "benefit": "how it saves time"
}"""

        elif pattern_type == "time_pattern":
            context = f"""Pattern: User consistently uses {pattern['app']} at {pattern['hour']}:00
Occurrences: {pattern['occurrences']} times over {pattern['days_active']} days
Confidence: {confidence:.2%}"""
            prompt = """Based on this time-based pattern, suggest an automation agent.

Consider:
- What might the user be doing at this time?
- Could preparation or reminders help?
- What could be automated or pre-configured?

Respond in JSON format:
{
    "agent_name": "descriptive name",
    "description": "what the agent does",
    "trigger": "when it should activate",
    "actions": ["list", "of", "actions"],
    "benefit": "how it saves time"
}"""

        elif pattern_type == "switch_pattern":
            context = f"""Pattern: User frequently switches from {pattern['from_app']} to {pattern['to_app']}
Frequency: {pattern['frequency']} times
Confidence: {confidence:.2%}"""
            prompt = """Based on this context-switching pattern, suggest an automation agent.

Consider:
- Why might the user switch between these apps?
- Could data be automatically transferred?
- What manual steps could be eliminated?

Respond in JSON format:
{
    "agent_name": "descriptive name",
    "description": "what the agent does",
    "trigger": "when it should activate",
    "actions": ["list", "of", "actions"],
    "benefit": "how it saves time"
}"""

        else:
            logger.warning(f"Unknown pattern type: {pattern_type}")
            return None

        try:
            # Query AI router
            response = await self.ai_router.query(
                prompt=prompt,
                context=context,
                complexity=TaskComplexity.MEDIUM,
                use_cache=True,
                cache_ttl=86400,  # 24 hours
                max_tokens=500,
            )

            # Parse JSON response
            suggestion_text = response["response"]

            # Try to extract JSON from response
            start = suggestion_text.find("{")
            end = suggestion_text.rfind("}") + 1

            if start >= 0 and end > start:
                suggestion_json = json.loads(suggestion_text[start:end])

                return {
                    "pattern_type": pattern_type,
                    "pattern_data": pattern["data"],
                    "confidence": confidence,
                    "suggestion": suggestion_json,
                    "created_at": utc_now(),
                }

        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse AI suggestion JSON",
                extra={"error": str(e), "response": suggestion_text},
            )
        except Exception as e:
            logger.error(
                "Failed to generate suggestion",
                extra={"error": str(e), "pattern_type": pattern_type},
            )

        return None
