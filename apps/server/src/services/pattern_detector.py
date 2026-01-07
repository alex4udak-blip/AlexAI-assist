"""Pattern detection service."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Event, Pattern


class PatternDetectorService:
    """Service for detecting behavior patterns from events."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def detect_patterns(
        self,
        device_id: str | None = None,
        min_occurrences: int = 3,
    ) -> list[dict[str, Any]]:
        """Detect repeating patterns in user behavior."""
        # Get recent events
        start_date = datetime.now(UTC) - timedelta(days=7)
        query = select(Event).where(Event.timestamp >= start_date)

        if device_id:
            query = query.where(Event.device_id == device_id)

        query = query.order_by(Event.timestamp)
        result = await self.db.execute(query)
        events = result.scalars().all()

        # Detect app sequence patterns
        app_sequences = self._detect_app_sequences(events, min_occurrences)

        # Detect time-based patterns
        time_patterns = self._detect_time_patterns(events, min_occurrences)

        # Detect context switch patterns
        context_switches = self._detect_context_switches(events)

        return {
            "app_sequences": app_sequences,
            "time_patterns": time_patterns,
            "context_switches": context_switches,
        }

    def _detect_app_sequences(
        self,
        events: list[Event],
        min_occurrences: int,
    ) -> list[dict[str, Any]]:
        """Detect repeating app usage sequences."""
        sequences: dict[tuple, int] = defaultdict(int)
        window_size = 3

        apps = [e.app_name for e in events if e.app_name]

        for i in range(len(apps) - window_size + 1):
            seq = tuple(apps[i : i + window_size])
            sequences[seq] += 1

        patterns = []
        for seq, count in sequences.items():
            if count >= min_occurrences:
                patterns.append({
                    "type": "app_sequence",
                    "sequence": list(seq),
                    "occurrences": count,
                    "automatable": len(set(seq)) > 1,
                })

        return sorted(patterns, key=lambda x: x["occurrences"], reverse=True)[:10]

    def _detect_time_patterns(
        self,
        events: list[Event],
        min_occurrences: int,
    ) -> list[dict[str, Any]]:
        """Detect patterns based on time of day."""
        hourly_apps: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for event in events:
            if event.app_name:
                hour = event.timestamp.hour
                hourly_apps[hour][event.app_name] += 1

        patterns = []
        for hour, apps in hourly_apps.items():
            top_app = max(apps.items(), key=lambda x: x[1]) if apps else None
            if top_app and top_app[1] >= min_occurrences:
                patterns.append({
                    "type": "time_based",
                    "hour": hour,
                    "app": top_app[0],
                    "occurrences": top_app[1],
                    "automatable": True,
                })

        return patterns

    def _detect_context_switches(
        self,
        events: list[Event],
    ) -> dict[str, Any]:
        """Analyze context switching behavior."""
        switches = 0
        previous_app = None

        for event in events:
            if event.app_name and event.app_name != previous_app:
                switches += 1
                previous_app = event.app_name

        total_events = len(events) or 1
        switch_rate = switches / total_events

        return {
            "total_switches": switches,
            "switch_rate": round(switch_rate, 3),
            "assessment": (
                "high" if switch_rate > 0.5
                else "medium" if switch_rate > 0.3
                else "low"
            ),
        }

    async def save_pattern(
        self,
        name: str,
        pattern_type: str,
        trigger_conditions: dict[str, Any],
        sequence: list[dict[str, Any]],
        occurrences: int = 0,
        automatable: bool = False,
    ) -> Pattern:
        """Save a detected pattern to the database."""
        pattern = Pattern(
            name=name,
            pattern_type=pattern_type,
            trigger_conditions=trigger_conditions,
            sequence=sequence,
            occurrences=occurrences,
            automatable=automatable,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        self.db.add(pattern)
        await self.db.flush()
        return pattern

    async def get_patterns(
        self,
        status: str | None = None,
        automatable: bool | None = None,
        limit: int = 50,
    ) -> list[Pattern]:
        """Get saved patterns from database."""
        query = select(Pattern).order_by(Pattern.occurrences.desc()).limit(limit)

        if status:
            query = query.where(Pattern.status == status)
        if automatable is not None:
            query = query.where(Pattern.automatable == automatable)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_pattern(self, pattern_id: UUID) -> Pattern | None:
        """Get a specific pattern by ID."""
        result = await self.db.execute(
            select(Pattern).where(Pattern.id == pattern_id)
        )
        return result.scalar_one_or_none()
