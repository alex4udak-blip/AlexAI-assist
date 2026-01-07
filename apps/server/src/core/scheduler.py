"""Background scheduler for periodic tasks."""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import distinct, select

from src.db.models import ChatMessage
from src.db.session import async_session_maker
from src.services.memory_service import MemoryService
from src.services.pattern_detector import PatternDetectorService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def detect_patterns_job() -> None:
    """Periodic job to detect patterns from recent events."""
    logger.info("Running scheduled pattern detection...")
    try:
        async with async_session_maker() as db:
            detector = PatternDetectorService(db)
            patterns = await detector.detect_patterns(min_occurrences=3)

            # Save new patterns to database
            for app_seq in patterns.get("app_sequences", [])[:5]:
                name = f"App sequence: {' -> '.join(app_seq['sequence'])}"
                await detector.save_pattern(
                    name=name,
                    pattern_type="app_sequence",
                    trigger_conditions={"sequence": app_seq["sequence"]},
                    sequence=[{"app": app} for app in app_seq["sequence"]],
                    occurrences=app_seq["occurrences"],
                    automatable=app_seq.get("automatable", False),
                )

            for time_pat in patterns.get("time_patterns", [])[:5]:
                name = f"Daily at {time_pat['hour']:02d}:00 - {time_pat['app']}"
                await detector.save_pattern(
                    name=name,
                    pattern_type="time_based",
                    trigger_conditions={"hour": time_pat["hour"]},
                    sequence=[{"app": time_pat["app"], "hour": time_pat["hour"]}],
                    occurrences=time_pat["occurrences"],
                    automatable=time_pat.get("automatable", False),
                )

            await db.commit()
            logger.info(f"Pattern detection complete. Found {len(patterns.get('app_sequences', []))} app sequences, {len(patterns.get('time_patterns', []))} time patterns")
    except Exception as e:
        logger.error(f"Pattern detection job failed: {e}")


async def daily_summary_job() -> None:
    """Create daily summaries for all active sessions."""
    logger.info("Creating daily summaries...")
    try:
        async with async_session_maker() as db:
            # Get all sessions with activity in the last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            query = (
                select(distinct(ChatMessage.session_id))
                .where(ChatMessage.timestamp >= yesterday)
            )
            result = await db.execute(query)
            sessions = [row[0] for row in result.all()]

            memory = MemoryService(db)
            for session_id in sessions:
                try:
                    await memory.create_daily_summary(session_id, datetime.utcnow())
                except Exception as e:
                    logger.error(f"Failed to create summary for {session_id}: {e}")

            await db.commit()
            logger.info(f"Created daily summaries for {len(sessions)} sessions")
    except Exception as e:
        logger.error(f"Daily summary job failed: {e}")


async def extract_insights_job() -> None:
    """Analyze patterns and create insights."""
    logger.info("Extracting insights from patterns...")
    try:
        async with async_session_maker() as db:
            detector = PatternDetectorService(db)
            patterns = await detector.detect_patterns(min_occurrences=5)

            # Create insights from detected patterns
            memory = MemoryService(db)
            context_switches = patterns.get("context_switches", {})

            if context_switches.get("assessment") == "high":
                from src.db.models import MemoryInsight
                from uuid import uuid4

                insight = MemoryInsight(
                    id=uuid4(),
                    session_id=None,  # Global insight
                    insight_type="optimization",
                    title="High context switching detected",
                    content=f"You're switching between apps frequently ({context_switches.get('switch_rate', 0):.1%}). Consider batching similar tasks.",
                    relevance_score=0.8,
                    created_at=datetime.utcnow(),
                )
                db.add(insight)

            await db.commit()
            logger.info("Insight extraction complete")
    except Exception as e:
        logger.error(f"Insight extraction job failed: {e}")


def start_scheduler() -> None:
    """Start the background scheduler."""
    # Run pattern detection every 5 minutes
    scheduler.add_job(
        detect_patterns_job,
        trigger=IntervalTrigger(minutes=5),
        id="detect_patterns",
        name="Detect behavior patterns",
        replace_existing=True,
    )

    # Run daily summary at midnight
    scheduler.add_job(
        daily_summary_job,
        trigger=CronTrigger(hour=0, minute=5),
        id="daily_summary",
        name="Create daily summaries",
        replace_existing=True,
    )

    # Extract insights every 6 hours
    scheduler.add_job(
        extract_insights_job,
        trigger=IntervalTrigger(hours=6),
        id="extract_insights",
        name="Extract insights from patterns",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Background scheduler stopped")
