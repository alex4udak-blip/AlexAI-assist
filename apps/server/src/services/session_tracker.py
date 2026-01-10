"""Session tracker service for detecting work sessions and breaks."""

import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.db.models import Event, Session

logger = get_logger(__name__)


def utc_now() -> datetime:
    """Get current UTC time as naive datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


class SessionTracker:
    """Track user work sessions and detect patterns."""

    # Default thresholds (configurable via environment variables)
    DEFAULT_SESSION_BREAK_MINUTES = 30
    DEFAULT_SHORT_BREAK_MINUTES = 5
    DEFAULT_MIN_SESSION_MINUTES = 5

    def __init__(self) -> None:
        """Initialize session tracker with configurable thresholds."""
        # Load configurable thresholds from environment variables
        self.SESSION_BREAK_MINUTES = int(
            os.getenv("SESSION_BREAK_MINUTES", self.DEFAULT_SESSION_BREAK_MINUTES)
        )
        self.SHORT_BREAK_MINUTES = int(
            os.getenv("SHORT_BREAK_MINUTES", self.DEFAULT_SHORT_BREAK_MINUTES)
        )
        self.MIN_SESSION_MINUTES = int(
            os.getenv("MIN_SESSION_MINUTES", self.DEFAULT_MIN_SESSION_MINUTES)
        )

        logger.info(
            "SessionTracker initialized",
            extra={
                "session_break_minutes": self.SESSION_BREAK_MINUTES,
                "short_break_minutes": self.SHORT_BREAK_MINUTES,
                "min_session_minutes": self.MIN_SESSION_MINUTES,
            },
        )

    async def process_event(
        self,
        event: Event,
        db: AsyncSession,
    ) -> dict[str, Any] | None:
        """
        Process a new event and update session tracking.

        Returns session info if a session boundary is detected.
        """
        device_id = event.device_id
        event_time = event.timestamp

        # Get the last active session for this device
        query = (
            select(Session)
            .where(Session.device_id == device_id)
            .where(Session.end_time.is_(None))
            .order_by(desc(Session.start_time))
            .limit(1)
        )
        result = await db.execute(query)
        active_session = result.scalar_one_or_none()

        if active_session:
            # Check time gap since last activity
            time_gap = (event_time - active_session.updated_at).total_seconds() / 60

            if time_gap >= self.SESSION_BREAK_MINUTES:
                # Long break detected - end current session, start new one
                await self._end_session(active_session, event_time, db)
                new_session = await self._start_session(device_id, event_time, event, db)

                logger.info(
                    "Session boundary detected",
                    extra={
                        "device_id": device_id,
                        "gap_minutes": time_gap,
                        "old_session_id": active_session.session_id,
                        "new_session_id": new_session.session_id,
                    },
                )

                return {
                    "event": "session_boundary",
                    "ended_session": active_session.session_id,
                    "started_session": new_session.session_id,
                    "break_duration_minutes": time_gap,
                }

            elif time_gap >= self.SHORT_BREAK_MINUTES:
                # Short break detected - update session but log the break
                await self._update_session(active_session, event, db)

                logger.debug(
                    "Short break detected",
                    extra={
                        "device_id": device_id,
                        "session_id": active_session.session_id,
                        "gap_minutes": time_gap,
                    },
                )

                return {
                    "event": "short_break",
                    "session_id": active_session.session_id,
                    "break_duration_minutes": time_gap,
                }

            else:
                # Normal activity - update session
                await self._update_session(active_session, event, db)

        else:
            # No active session - start a new one
            new_session = await self._start_session(device_id, event_time, event, db)

            logger.info(
                "New session started",
                extra={
                    "device_id": device_id,
                    "session_id": new_session.session_id,
                },
            )

            return {
                "event": "session_start",
                "session_id": new_session.session_id,
            }

        return None

    async def _start_session(
        self,
        device_id: str,
        start_time: datetime,
        event: Event,
        db: AsyncSession,
    ) -> Session:
        """Create a new session."""
        session_id = f"{device_id}_{int(start_time.timestamp())}"

        apps_used = [event.app_name] if event.app_name else []

        session = Session(
            session_id=session_id,
            device_id=device_id,
            start_time=start_time,
            apps_used=apps_used,
            events_count=1,
            metadata={
                "first_event_type": event.event_type,
                "first_app": event.app_name,
            },
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session

    async def _update_session(
        self,
        session: Session,
        event: Event,
        db: AsyncSession,
    ) -> None:
        """Update an active session with new event data."""
        # Update apps_used list
        if event.app_name and event.app_name not in session.apps_used:
            session.apps_used = session.apps_used + [event.app_name]

        # Increment event count
        session.events_count += 1

        # Update timestamp
        session.updated_at = event.timestamp

        await db.commit()

    async def _end_session(
        self,
        session: Session,
        end_time: datetime,
        db: AsyncSession,
    ) -> None:
        """End an active session and calculate metrics."""
        session.end_time = end_time

        # Calculate duration
        duration = (end_time - session.start_time).total_seconds() / 60
        session.duration_minutes = duration

        # Calculate productivity score (0-1)
        # Simple heuristic: based on events per minute and app diversity
        if duration > 0:
            events_per_minute = session.events_count / duration
            app_diversity = len(session.apps_used)

            # Score components
            activity_score = min(events_per_minute / 2.0, 1.0)  # 2 events/min = 100%
            diversity_score = min(app_diversity / 5.0, 1.0)  # 5 apps = 100%

            # Weight: 70% activity, 30% diversity
            session.productivity_score = 0.7 * activity_score + 0.3 * diversity_score
        else:
            session.productivity_score = 0.0

        await db.commit()

    async def end_inactive_sessions(
        self,
        db: AsyncSession,
        device_id: str | None = None,
    ) -> list[str]:
        """
        End sessions that have been inactive for too long.

        Returns list of ended session IDs.
        """
        cutoff_time = utc_now() - timedelta(minutes=self.SESSION_BREAK_MINUTES)

        query = (
            select(Session)
            .where(Session.end_time.is_(None))
            .where(Session.updated_at < cutoff_time)
        )

        if device_id:
            query = query.where(Session.device_id == device_id)

        result = await db.execute(query)
        inactive_sessions = result.scalars().all()

        ended_session_ids = []
        for session in inactive_sessions:
            await self._end_session(session, session.updated_at, db)
            ended_session_ids.append(session.session_id)

            logger.info(
                "Ended inactive session",
                extra={
                    "session_id": session.session_id,
                    "device_id": session.device_id,
                },
            )

        return ended_session_ids

    async def get_session_summary(
        self,
        db: AsyncSession,
        device_id: str,
        days: int = 7,
    ) -> dict[str, Any]:
        """Get summary statistics for sessions over a time period."""
        start_date = utc_now() - timedelta(days=days)

        query = (
            select(Session)
            .where(Session.device_id == device_id)
            .where(Session.start_time >= start_date)
            .order_by(desc(Session.start_time))
        )

        result = await db.execute(query)
        sessions = result.scalars().all()

        if not sessions:
            return {
                "total_sessions": 0,
                "total_minutes": 0,
                "avg_session_minutes": 0,
                "avg_productivity_score": 0,
                "most_used_apps": [],
            }

        # Calculate statistics
        total_minutes = sum(s.duration_minutes or 0 for s in sessions)
        completed_sessions = [s for s in sessions if s.end_time is not None]

        avg_productivity = 0.0
        if completed_sessions:
            scores = [s.productivity_score for s in completed_sessions if s.productivity_score]
            if scores:
                avg_productivity = sum(scores) / len(scores)

        # Count app usage across all sessions
        app_counts: dict[str, int] = defaultdict(int)
        for session in sessions:
            for app in session.apps_used:
                app_counts[app] += 1

        most_used_apps = sorted(
            app_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return {
            "total_sessions": len(sessions),
            "total_minutes": round(total_minutes, 1),
            "avg_session_minutes": round(total_minutes / len(sessions), 1) if sessions else 0,
            "avg_productivity_score": round(avg_productivity, 2),
            "most_used_apps": [{"app": app, "count": count} for app, count in most_used_apps],
            "active_sessions": len([s for s in sessions if s.end_time is None]),
        }

    async def detect_session_patterns(
        self,
        db: AsyncSession,
        device_id: str,
        days: int = 7,
    ) -> dict[str, Any]:
        """Detect patterns in user sessions (peak hours, session length trends, etc.)."""
        start_date = utc_now() - timedelta(days=days)

        query = (
            select(Session)
            .where(Session.device_id == device_id)
            .where(Session.start_time >= start_date)
            .where(Session.end_time.is_not(None))
        )

        result = await db.execute(query)
        sessions = result.scalars().all()

        if not sessions:
            return {"patterns_found": False}

        # Analyze start times by hour
        hourly_sessions: dict[int, int] = defaultdict(int)
        for session in sessions:
            hour = session.start_time.hour
            hourly_sessions[hour] += 1

        # Find peak hours (top 3)
        peak_hours = sorted(
            hourly_sessions.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        # Analyze session durations
        durations = [s.duration_minutes for s in sessions if s.duration_minutes]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Analyze productivity trends
        productivity_scores = [s.productivity_score for s in sessions if s.productivity_score]
        avg_productivity = sum(productivity_scores) / len(productivity_scores) if productivity_scores else 0

        return {
            "patterns_found": True,
            "peak_hours": [{"hour": hour, "sessions": count} for hour, count in peak_hours],
            "avg_session_duration_minutes": round(avg_duration, 1),
            "avg_productivity_score": round(avg_productivity, 2),
            "total_sessions_analyzed": len(sessions),
            "days_analyzed": days,
        }
