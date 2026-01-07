"""Event analyzer service."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Event


class AnalyzerService:
    """Service for analyzing user activity events."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(
        self,
        device_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get activity summary statistics."""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()

        query = select(Event).where(
            Event.timestamp >= start_date,
            Event.timestamp <= end_date,
        )

        if device_id:
            query = query.where(Event.device_id == device_id)

        result = await self.db.execute(query)
        events = result.scalars().all()

        # Calculate statistics
        total_events = len(events)
        apps_used: dict[str, int] = defaultdict(int)
        categories: dict[str, int] = defaultdict(int)
        hourly_activity: dict[int, int] = defaultdict(int)

        for event in events:
            if event.app_name:
                apps_used[event.app_name] += 1
            if event.category:
                categories[event.category] += 1
            hourly_activity[event.timestamp.hour] += 1

        return {
            "total_events": total_events,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "top_apps": sorted(
                apps_used.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10],
            "categories": dict(categories),
            "hourly_activity": dict(hourly_activity),
        }

    async def get_category_breakdown(
        self,
        device_id: str | None = None,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Get time spent by category."""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = (
            select(
                Event.category,
                func.count(Event.id).label("count"),
            )
            .where(Event.timestamp >= start_date)
            .group_by(Event.category)
        )

        if device_id:
            query = query.where(Event.device_id == device_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {"category": row.category or "uncategorized", "count": row.count}
            for row in rows
        ]

    async def get_app_usage(
        self,
        device_id: str | None = None,
        days: int = 7,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get app usage statistics."""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = (
            select(
                Event.app_name,
                func.count(Event.id).label("event_count"),
            )
            .where(
                Event.timestamp >= start_date,
                Event.app_name.isnot(None),
            )
            .group_by(Event.app_name)
            .order_by(func.count(Event.id).desc())
            .limit(limit)
        )

        if device_id:
            query = query.where(Event.device_id == device_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {"app_name": row.app_name, "event_count": row.event_count}
            for row in rows
        ]

    async def get_productivity_score(
        self,
        device_id: str | None = None,
    ) -> dict[str, Any]:
        """Calculate productivity score based on activity patterns."""
        today = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        query = select(Event).where(Event.timestamp >= today)

        if device_id:
            query = query.where(Event.device_id == device_id)

        result = await self.db.execute(query)
        events = result.scalars().all()

        # Calculate productivity metrics
        productive_categories = {"coding", "writing", "design", "research"}
        productive_count = sum(
            1 for e in events if e.category in productive_categories
        )
        total_count = len(events) or 1

        score = int((productive_count / total_count) * 100)

        return {
            "score": min(score, 100),
            "productive_events": productive_count,
            "total_events": len(events),
            "trend": "up" if score > 50 else "down",
        }

    async def get_trends(
        self,
        device_id: str | None = None,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get activity trends over time."""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = (
            select(
                func.date_trunc("day", Event.timestamp).label("date"),
                func.count(Event.id).label("count"),
            )
            .where(Event.timestamp >= start_date)
            .group_by(func.date_trunc("day", Event.timestamp))
            .order_by(func.date_trunc("day", Event.timestamp))
        )

        if device_id:
            query = query.where(Event.device_id == device_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {"date": row.date.isoformat(), "count": row.count}
            for row in rows
        ]
