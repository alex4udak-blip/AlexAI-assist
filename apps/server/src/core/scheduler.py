"""Background scheduler for periodic tasks."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
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
            seq_count = len(patterns.get('app_sequences', []))
            time_count = len(patterns.get('time_patterns', []))
            logger.info(f"Pattern detection complete. Found {seq_count} app sequences, {time_count} time patterns")
    except Exception as e:
        logger.error(f"Pattern detection job failed: {e}")


async def memory_consolidation_job() -> None:
    """Hourly job to consolidate memory system."""
    logger.info("Running scheduled memory consolidation...")
    try:
        from src.services.memory import MemoryManager

        async with async_session_maker() as db:
            manager = MemoryManager(db, session_id="default")
            result = await manager.consolidate()
            await db.commit()
            logger.info(f"Memory consolidation complete: {result}")
    except Exception as e:
        logger.error(f"Memory consolidation job failed: {e}")


async def memory_decay_job() -> None:
    """Daily job to apply heat decay to memories."""
    logger.info("Running scheduled memory decay...")
    try:
        from src.services.memory.memory_scheduler import MemScheduler

        async with async_session_maker() as db:
            scheduler_svc = MemScheduler(db, session_id="default")
            result = await scheduler_svc.apply_decay()
            await db.commit()
            logger.info(f"Memory decay complete: {result}")
    except Exception as e:
        logger.error(f"Memory decay job failed: {e}")


async def belief_evolution_job() -> None:
    """Weekly job to evolve beliefs based on evidence."""
    logger.info("Running scheduled belief evolution...")
    try:
        from src.services.memory.belief_network import BeliefNetwork

        async with async_session_maker() as db:
            belief_net = BeliefNetwork(db, session_id="default")
            modified = await belief_net.evolve_from_evidence()
            await db.commit()
            logger.info(f"Belief evolution complete: {modified} beliefs modified")
    except Exception as e:
        logger.error(f"Belief evolution job failed: {e}")


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

    # Run memory consolidation every hour
    scheduler.add_job(
        memory_consolidation_job,
        trigger=CronTrigger(minute=0),
        id="memory_consolidation",
        name="Consolidate memory system",
        replace_existing=True,
    )

    # Run memory decay daily at 3 AM
    scheduler.add_job(
        memory_decay_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="memory_decay",
        name="Apply memory decay",
        replace_existing=True,
    )

    # Run belief evolution weekly on Sunday at 4 AM
    scheduler.add_job(
        belief_evolution_job,
        trigger=CronTrigger(day_of_week="sun", hour=4, minute=0),
        id="belief_evolution",
        name="Evolve beliefs from evidence",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Background scheduler started with memory jobs")


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Background scheduler stopped")
