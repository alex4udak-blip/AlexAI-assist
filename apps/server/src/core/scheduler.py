"""Background scheduler for periodic tasks."""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.db.session import async_session_maker
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

    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Background scheduler stopped")
