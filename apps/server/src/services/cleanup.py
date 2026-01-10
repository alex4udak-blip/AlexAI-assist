"""Data retention cleanup service."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    AuditLog,
    ChatMessage,
    Event,
    Session,
)

logger = logging.getLogger(__name__)


class CleanupService:
    """Service for cleaning up old data based on retention policy."""

    # Tables to clean and their timestamp columns
    CLEANUP_TARGETS: list[tuple[Any, str]] = [
        (Event, "timestamp"),
        (Session, "start_time"),
        (ChatMessage, "timestamp"),
        (AuditLog, "timestamp"),
    ]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def cleanup(
        self,
        retention_days: int = 30,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Delete data older than retention period.

        Args:
            retention_days: Number of days to retain data. Default is 30.
            dry_run: If True, only count records without deleting.

        Returns:
            Dictionary with cleanup results per table.
        """
        cutoff_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            days=retention_days
        )

        results: dict[str, Any] = {
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "dry_run": dry_run,
            "tables": {},
        }

        total_deleted = 0

        for model, timestamp_col in self.CLEANUP_TARGETS:
            table_name = model.__tablename__
            timestamp_column = getattr(model, timestamp_col)

            try:
                # Count records to be deleted
                count_query = select(func.count()).select_from(model).where(
                    timestamp_column < cutoff_date
                )
                count_result = await self.db.execute(count_query)
                count = count_result.scalar() or 0

                if dry_run:
                    results["tables"][table_name] = {
                        "would_delete": count,
                        "status": "dry_run",
                    }
                else:
                    if count > 0:
                        # Delete old records
                        delete_query = delete(model).where(
                            timestamp_column < cutoff_date
                        )
                        await self.db.execute(delete_query)
                        total_deleted += count

                    results["tables"][table_name] = {
                        "deleted": count,
                        "status": "success",
                    }

                logger.info(
                    f"Cleanup {table_name}: {'would delete' if dry_run else 'deleted'} {count} records"
                )

            except Exception as e:
                logger.error(f"Cleanup failed for {table_name}: {e}")
                results["tables"][table_name] = {
                    "deleted": 0,
                    "status": "error",
                    "error": str(e),
                }

        if not dry_run:
            await self.db.commit()
            results["total_deleted"] = total_deleted
        else:
            results["total_would_delete"] = sum(
                t.get("would_delete", 0) for t in results["tables"].values()
            )

        return results

    async def get_storage_stats(self) -> dict[str, Any]:
        """Get storage statistics for all tables.

        Returns:
            Dictionary with record counts per table.
        """
        stats: dict[str, Any] = {"tables": {}}
        total_records = 0

        for model, timestamp_col in self.CLEANUP_TARGETS:
            table_name = model.__tablename__
            timestamp_column = getattr(model, timestamp_col)

            try:
                # Total count
                count_query = select(func.count()).select_from(model)
                count_result = await self.db.execute(count_query)
                count = count_result.scalar() or 0

                # Oldest record
                oldest_query = select(func.min(timestamp_column))
                oldest_result = await self.db.execute(oldest_query)
                oldest = oldest_result.scalar()

                # Newest record
                newest_query = select(func.max(timestamp_column))
                newest_result = await self.db.execute(newest_query)
                newest = newest_result.scalar()

                stats["tables"][table_name] = {
                    "count": count,
                    "oldest": oldest.isoformat() if oldest else None,
                    "newest": newest.isoformat() if newest else None,
                }
                total_records += count

            except Exception as e:
                logger.error(f"Failed to get stats for {table_name}: {e}")
                stats["tables"][table_name] = {
                    "count": 0,
                    "error": str(e),
                }

        stats["total_records"] = total_records
        return stats
