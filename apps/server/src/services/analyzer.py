"""Event analyzer service."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Integer, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Event


def _get_dialect_name(session: AsyncSession) -> str:
    """Get the database dialect name from the session."""
    bind = session.get_bind()
    return bind.dialect.name


def _extract_hour(timestamp_col: Any, dialect_name: str) -> Any:
    """Extract hour from timestamp, compatible with PostgreSQL and SQLite."""
    if dialect_name == "sqlite":
        return func.cast(func.strftime("%H", timestamp_col), Integer)
    return func.extract("hour", timestamp_col)


def _date_trunc_day(timestamp_col: Any, dialect_name: str) -> Any:
    """Truncate timestamp to day, compatible with PostgreSQL and SQLite."""
    if dialect_name == "sqlite":
        return func.date(timestamp_col)
    return func.date_trunc("day", timestamp_col)


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
        """Get activity summary statistics using SQL aggregations."""
        if not start_date:
            start_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
        if not end_date:
            end_date = datetime.now(UTC).replace(tzinfo=None)

        # Base filter conditions
        base_conditions = [
            Event.timestamp >= start_date,
            Event.timestamp <= end_date,
        ]
        if device_id:
            base_conditions.append(Event.device_id == device_id)

        # OPTIMIZATION NOTE: These queries cannot be combined into one because:
        # 1. Each GROUP BY produces different result shapes (apps, categories, hours)
        # 2. Combining them would require UNION which loses type information
        # 3. Using multiple aggregations in one query would produce cartesian products
        # The total_events is derived from categories query to save one round-trip.

        # Query 1: Get category breakdown (GROUP BY category) + total via window
        # This also gives us total_events without a separate query
        categories_query = (
            select(
                Event.category,
                func.count(Event.id).label("count"),
                func.sum(func.count(Event.id)).over().label("total"),
            )
            .where(*base_conditions, Event.category.isnot(None))
            .group_by(Event.category)
        )
        categories_result = await self.db.execute(categories_query)
        categories_rows = categories_result.all()
        categories = {row.category: row.count for row in categories_rows}
        # Get total from first row's window function, or query if no categories
        total_events = categories_rows[0].total if categories_rows else 0

        # If no categorized events, we still need accurate total count
        if not categories_rows:
            total_query = select(func.count(Event.id)).where(*base_conditions)
            total_result = await self.db.execute(total_query)
            total_events = total_result.scalar() or 0

        # Query 2: Get top apps (GROUP BY app_name)
        # Cannot combine with categories - different grouping dimension
        apps_query = (
            select(
                Event.app_name,
                func.count(Event.id).label("count"),
            )
            .where(*base_conditions, Event.app_name.isnot(None))
            .group_by(Event.app_name)
            .order_by(func.count(Event.id).desc())
            .limit(10)
        )
        apps_result = await self.db.execute(apps_query)
        top_apps = [(row.app_name, row.count) for row in apps_result.all()]

        # Query 3: Get hourly activity (GROUP BY hour)
        # Cannot combine - requires temporal extraction which differs by dialect
        dialect_name = _get_dialect_name(self.db)
        hour_expr = _extract_hour(Event.timestamp, dialect_name)
        hourly_query = (
            select(
                hour_expr.label("hour"),
                func.count(Event.id).label("count"),
            )
            .where(*base_conditions)
            .group_by(hour_expr)
        )
        hourly_result = await self.db.execute(hourly_query)
        hourly_activity = {int(row.hour): row.count for row in hourly_result.all()}

        return {
            "total_events": total_events,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "top_apps": top_apps,
            "categories": categories,
            "hourly_activity": hourly_activity,
        }

    async def get_category_breakdown(
        self,
        device_id: str | None = None,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Get time spent by category."""
        start_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

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
        """Get app usage statistics using SQL aggregation."""
        start_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

        # Use SQL GROUP BY for efficient aggregation
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
        days: int = 7,
    ) -> dict[str, Any]:
        """Calculate productivity score using SQL aggregations."""
        start_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

        # Define productivity categories
        productive_categories = ("coding", "writing", "design", "research")
        semi_productive_categories = ("browsing", "reading")

        # Base conditions
        base_conditions = [Event.timestamp >= start_date]
        if device_id:
            base_conditions.append(Event.device_id == device_id)

        # Use SQL CASE expressions for conditional counting
        productive_case = case(
            (Event.category.in_(productive_categories), 1),
            else_=0,
        )
        semi_productive_case = case(
            (Event.category.in_(semi_productive_categories), 1),
            else_=0,
        )

        # Single query to get all counts using SQL aggregations
        query = select(
            func.count(Event.id).label("total_count"),
            func.sum(productive_case).label("productive_count"),
            func.sum(semi_productive_case).label("semi_productive_count"),
        ).where(*base_conditions)

        result = await self.db.execute(query)
        row = result.one()

        total_count = row.total_count or 0
        productive_count = row.productive_count or 0
        semi_productive_count = row.semi_productive_count or 0

        # Calculate weighted score: full for productive, 0.5 for semi-productive
        if total_count > 0:
            weighted_count = productive_count + (semi_productive_count * 0.5)
            score = int((weighted_count / total_count) * 100)
        else:
            score = 0

        return {
            "score": min(score, 100),
            "productive_events": productive_count,
            "total_events": total_count,
            "trend": "up" if score > 50 else "down",
        }

    async def get_recent_activity_details(
        self,
        device_id: str | None = None,
        hours: int = 4,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get recent detailed activity for AI context.

        Returns recent events with full details:
        - App names, window titles, URLs
        - Typed text in browsers
        - Timestamps
        """
        start_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)

        conditions = [Event.timestamp >= start_time]
        if device_id:
            conditions.append(Event.device_id == device_id)

        query = (
            select(Event)
            .where(*conditions)
            .order_by(Event.timestamp.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        events = result.scalars().all()

        detailed_activity = []
        for event in events:
            activity = {
                "timestamp": event.timestamp.strftime("%H:%M"),
                "app": event.app_name,
                "title": event.window_title,
            }

            # Add URL if present
            if event.url:
                activity["url"] = event.url

            # Add typed text if present (browser search/input)
            typed_text = event.data.get("typed_text") if event.data else None
            if typed_text:
                activity["typed"] = str(typed_text)[:200]  # Truncate for context

            # Add category
            if event.category:
                activity["category"] = event.category

            detailed_activity.append(activity)

        return detailed_activity

    async def get_trends(
        self,
        device_id: str | None = None,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get activity trends over time."""
        start_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

        dialect_name = _get_dialect_name(self.db)
        date_trunc_expr = _date_trunc_day(Event.timestamp, dialect_name)
        query = (
            select(
                date_trunc_expr.label("date"),
                func.count(Event.id).label("count"),
            )
            .where(Event.timestamp >= start_date)
            .group_by(date_trunc_expr)
            .order_by(date_trunc_expr)
        )

        if device_id:
            query = query.where(Event.device_id == device_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {"date": row.date.isoformat(), "count": row.count}
            for row in rows
        ]
