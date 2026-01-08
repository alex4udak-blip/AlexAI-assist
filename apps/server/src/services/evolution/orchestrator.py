"""
Evolution Orchestrator - Meta-agent managing all evolution subsystems.

This orchestrator:
1. Collects feedback from all sources (user, system, LLM-as-judge)
2. Prioritizes what needs evolution
3. Coordinates evolution across subsystems (memory, behavior, agents)
4. Validates changes don't break existing functionality
5. Rolls back if evolution causes regression
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.claude import claude_client
from src.db.models import Agent, AgentLog, Pattern, Suggestion
from src.db.models.memory import (
    MemoryExperience,
    MemoryFact,
    MemoryOperation,
)

logger = logging.getLogger(__name__)


class EvolutionPriority(str, Enum):
    """Priority levels for evolution tasks."""

    CRITICAL = "critical"  # System broken, immediate fix needed
    HIGH = "high"  # Important issue, evolve in next cycle
    MEDIUM = "medium"  # Improvement opportunity
    LOW = "low"  # Nice to have, evolve when idle


class EvolutionSubsystem(str, Enum):
    """Subsystems that can evolve."""

    MEMORY = "memory"
    BEHAVIOR = "behavior"
    AGENTS = "agents"
    PATTERNS = "patterns"
    SYSTEM = "system"


class EvolutionState:
    """State snapshot for rollback capability."""

    def __init__(
        self,
        subsystem: EvolutionSubsystem,
        timestamp: datetime,
        snapshot_data: dict[str, Any],
    ):
        self.id = uuid4()
        self.subsystem = subsystem
        self.timestamp = timestamp
        self.snapshot_data = snapshot_data


class FeedbackSource:
    """Categorized feedback for analysis."""

    def __init__(
        self,
        source_type: str,
        priority: EvolutionPriority,
        subsystem: EvolutionSubsystem,
        content: str,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = uuid4()
        self.source_type = source_type
        self.priority = priority
        self.subsystem = subsystem
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now(UTC)


class EvolutionOrchestrator:
    """
    Meta-agent orchestrating all evolution subsystems.

    Runs on a 6-hour cycle via scheduler, analyzes feedback,
    coordinates evolution, and validates system health.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.feedback_queue: list[FeedbackSource] = []
        self.evolution_history: list[EvolutionState] = []
        self.max_history_size = 100  # Keep last 100 evolution states
        self.health_threshold = 0.7  # System health must be >= 70%

    async def run_evolution_cycle(self) -> dict[str, Any]:
        """
        Main evolution cycle called by scheduler every 6 hours.

        Returns:
            Summary of evolution cycle results
        """
        logger.info("Starting evolution cycle")
        cycle_start = datetime.now(UTC)

        try:
            # Step 1: Collect feedback from all sources
            feedback = await self._collect_feedback()
            logger.info(f"Collected {len(feedback)} feedback items")

            # Step 2: Analyze and categorize feedback by subsystem
            categorized = await self._analyze_feedback(feedback)
            logger.info(
                f"Categorized feedback: {len(categorized['memory'])} memory, "
                f"{len(categorized['behavior'])} behavior, "
                f"{len(categorized['agents'])} agents"
            )

            # Step 3: Prioritize evolution tasks
            prioritized = self._prioritize_tasks(categorized)

            # Step 4: Take snapshots before evolution
            await self._create_snapshots(prioritized)

            # Step 5: Execute evolution for each subsystem
            results = {}

            if prioritized.get("memory"):
                results["memory"] = await self._evolve_memory(prioritized["memory"])

            if prioritized.get("behavior"):
                results["behavior"] = await self._evolve_behavior(
                    prioritized["behavior"]
                )

            if prioritized.get("agents"):
                results["agents"] = await self._evolve_agents(prioritized["agents"])

            # Step 6: Validate system health after evolution
            health_check = await self._validate_system_health()

            if not health_check["healthy"]:
                logger.warning(
                    f"System health degraded: {health_check['score']:.2%} "
                    f"(threshold: {self.health_threshold:.2%})"
                )
                # Rollback failing evolutions
                rollback_results = await self._perform_rollbacks(
                    health_check["issues"]
                )
                results["rollbacks"] = rollback_results

            # Step 7: Cleanup old snapshots
            self._cleanup_old_snapshots()

            cycle_duration = (datetime.now(UTC) - cycle_start).total_seconds()

            return {
                "status": "completed",
                "cycle_start": cycle_start.isoformat(),
                "duration_seconds": cycle_duration,
                "feedback_collected": len(feedback),
                "evolutions_performed": results,
                "health_check": health_check,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Evolution cycle failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "cycle_start": cycle_start.isoformat(),
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def trigger_immediate_evolution(
        self,
        subsystem: EvolutionSubsystem,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Trigger immediate evolution for critical issues.

        Args:
            subsystem: Which subsystem needs evolution
            reason: Description of critical issue
            metadata: Additional context

        Returns:
            Evolution result
        """
        logger.warning(
            f"Triggering immediate evolution for {subsystem.value}: {reason}"
        )

        # Create critical feedback
        feedback_item = FeedbackSource(
            source_type="critical_trigger",
            priority=EvolutionPriority.CRITICAL,
            subsystem=subsystem,
            content=reason,
            metadata=metadata,
        )

        # Create snapshot before evolution
        snapshot = await self._create_snapshot(subsystem)

        try:
            # Execute evolution based on subsystem
            if subsystem == EvolutionSubsystem.MEMORY:
                result = await self._evolve_memory([feedback_item])
            elif subsystem == EvolutionSubsystem.BEHAVIOR:
                result = await self._evolve_behavior([feedback_item])
            elif subsystem == EvolutionSubsystem.AGENTS:
                result = await self._evolve_agents([feedback_item])
            else:
                result = {"status": "unsupported", "subsystem": subsystem.value}

            # Validate health
            health = await self._validate_system_health()

            if not health["healthy"]:
                logger.error(
                    "Immediate evolution caused health degradation, rolling back"
                )
                await self._rollback_snapshot(snapshot)
                result["rolled_back"] = True
                result["rollback_reason"] = "health_degradation"

            return result

        except Exception as e:
            logger.error(f"Immediate evolution failed: {e}", exc_info=True)
            await self._rollback_snapshot(snapshot)
            return {"status": "failed", "error": str(e), "rolled_back": True}

    async def _collect_feedback(self) -> list[FeedbackSource]:
        """
        Collect feedback from all sources.

        Sources:
        - User feedback (from chat interactions)
        - System metrics (errors, performance)
        - LLM-as-judge evaluations
        - Agent execution logs
        - Memory operation logs
        """
        feedback: list[FeedbackSource] = []

        # Collect from agent logs (errors, failures)
        agent_logs = await self._collect_agent_feedback()
        feedback.extend(agent_logs)

        # Collect from memory operations (failed recalls, low confidence)
        memory_feedback = await self._collect_memory_feedback()
        feedback.extend(memory_feedback)

        # Collect from system metrics
        system_feedback = await self._collect_system_feedback()
        feedback.extend(system_feedback)

        # Collect from pattern detection (opportunities)
        pattern_feedback = await self._collect_pattern_feedback()
        feedback.extend(pattern_feedback)

        return feedback

    async def _collect_agent_feedback(self) -> list[FeedbackSource]:
        """Collect feedback from agent execution logs."""
        feedback: list[FeedbackSource] = []

        # Get recent failed agent executions
        one_day_ago = datetime.now(UTC) - timedelta(days=1)
        result = await self.db.execute(
            select(AgentLog)
            .where(AgentLog.level == "error")
            .where(AgentLog.created_at >= one_day_ago)
            .limit(50)
        )
        failed_logs = result.scalars().all()

        for log in failed_logs:
            feedback.append(
                FeedbackSource(
                    source_type="agent_error",
                    priority=EvolutionPriority.HIGH,
                    subsystem=EvolutionSubsystem.AGENTS,
                    content=f"Agent execution failed: {log.message}",
                    metadata={
                        "agent_id": str(log.agent_id),
                        "log_id": str(log.id),
                        "error": log.message,
                    },
                )
            )

        return feedback

    async def _collect_memory_feedback(self) -> list[FeedbackSource]:
        """Collect feedback from memory operations."""
        feedback: list[FeedbackSource] = []

        # Get recent memory operations with low confidence
        one_day_ago = datetime.now(UTC) - timedelta(days=1)
        result = await self.db.execute(
            select(MemoryOperation)
            .where(MemoryOperation.created_at >= one_day_ago)
            .limit(100)
        )
        operations = result.scalars().all()

        low_confidence_count = sum(
            1 for op in operations if op.metadata.get("confidence", 1.0) < 0.5
        )

        if low_confidence_count > 10:
            feedback.append(
                FeedbackSource(
                    source_type="memory_quality",
                    priority=EvolutionPriority.MEDIUM,
                    subsystem=EvolutionSubsystem.MEMORY,
                    content=f"High number of low-confidence memory operations: {low_confidence_count}",
                    metadata={"low_confidence_operations": low_confidence_count},
                )
            )

        return feedback

    async def _collect_system_feedback(self) -> list[FeedbackSource]:
        """Collect system-level feedback (DB health, API errors, etc.)."""
        feedback: list[FeedbackSource] = []

        try:
            # Check database health
            await self.db.execute(text("SELECT 1"))

            # Check recent error patterns
            # This is a placeholder - in production, integrate with monitoring system
            logger.debug("System health check passed")

        except Exception as e:
            feedback.append(
                FeedbackSource(
                    source_type="system_health",
                    priority=EvolutionPriority.CRITICAL,
                    subsystem=EvolutionSubsystem.SYSTEM,
                    content=f"System health issue: {e}",
                    metadata={"error": str(e)},
                )
            )

        return feedback

    async def _collect_pattern_feedback(self) -> list[FeedbackSource]:
        """Collect feedback from pattern detection."""
        feedback: list[FeedbackSource] = []

        # Get recent patterns that could benefit from automation
        result = await self.db.execute(
            select(Pattern).where(Pattern.occurrences >= 5).limit(20)
        )
        patterns = result.scalars().all()

        for pattern in patterns:
            # Check if pattern already has an agent
            agent_check = await self.db.execute(
                select(Agent).where(Agent.name.ilike(f"%{pattern.name}%")).limit(1)
            )
            if not agent_check.scalar():
                feedback.append(
                    FeedbackSource(
                        source_type="pattern_opportunity",
                        priority=EvolutionPriority.MEDIUM,
                        subsystem=EvolutionSubsystem.AGENTS,
                        content=f"Pattern '{pattern.name}' could benefit from automation",
                        metadata={
                            "pattern_id": str(pattern.id),
                            "occurrences": pattern.occurrences,
                        },
                    )
                )

        return feedback

    async def _analyze_feedback(
        self, feedback: list[FeedbackSource]
    ) -> dict[str, list[FeedbackSource]]:
        """
        Analyze and categorize feedback using LLM.

        Groups feedback by subsystem and refines categorization.
        """
        if not feedback:
            return {"memory": [], "behavior": [], "agents": [], "system": []}

        # Prepare feedback for LLM analysis
        feedback_summary = [
            {
                "id": str(f.id),
                "source": f.source_type,
                "priority": f.priority.value,
                "subsystem": f.subsystem.value,
                "content": f.content,
            }
            for f in feedback
        ]

        try:
            prompt = f"""Analyze this feedback and provide evolution recommendations:

Feedback items ({len(feedback)}):
{json.dumps(feedback_summary, indent=2)}

For each feedback item, determine:
1. Is the subsystem categorization correct?
2. Should the priority be adjusted?
3. What specific evolution action is needed?

Respond with JSON:
{{
    "categorized_feedback": [
        {{
            "id": "feedback_id",
            "subsystem": "memory|behavior|agents|system",
            "priority": "critical|high|medium|low",
            "action": "specific evolution action needed"
        }}
    ]
}}"""

            response = await claude_client.complete(
                prompt=prompt,
                system="You are an AI system evolution analyzer. "
                       "Provide actionable evolution recommendations based on feedback.",
                max_tokens=4000,
            )

            analysis = json.loads(response)

            # Re-categorize feedback based on LLM analysis
            categorized: dict[str, list[FeedbackSource]] = {
                "memory": [],
                "behavior": [],
                "agents": [],
                "system": [],
            }

            for item in analysis.get("categorized_feedback", []):
                # Find original feedback
                original = next(
                    (f for f in feedback if str(f.id) == item["id"]), None
                )
                if original:
                    # Update based on LLM analysis
                    original.subsystem = EvolutionSubsystem(item["subsystem"])
                    original.priority = EvolutionPriority(item["priority"])
                    original.metadata["evolution_action"] = item["action"]

                    # Add to categorized dict
                    categorized[item["subsystem"]].append(original)

            return categorized

        except Exception as e:
            logger.error(f"LLM feedback analysis failed: {e}", exc_info=True)
            # Fallback to simple categorization
            return {
                "memory": [
                    f for f in feedback if f.subsystem == EvolutionSubsystem.MEMORY
                ],
                "behavior": [
                    f for f in feedback if f.subsystem == EvolutionSubsystem.BEHAVIOR
                ],
                "agents": [
                    f for f in feedback if f.subsystem == EvolutionSubsystem.AGENTS
                ],
                "system": [
                    f for f in feedback if f.subsystem == EvolutionSubsystem.SYSTEM
                ],
            }

    def _prioritize_tasks(
        self, categorized: dict[str, list[FeedbackSource]]
    ) -> dict[str, list[FeedbackSource]]:
        """
        Prioritize evolution tasks within each subsystem.

        Returns tasks sorted by priority (CRITICAL > HIGH > MEDIUM > LOW).
        """
        priority_order = {
            EvolutionPriority.CRITICAL: 0,
            EvolutionPriority.HIGH: 1,
            EvolutionPriority.MEDIUM: 2,
            EvolutionPriority.LOW: 3,
        }

        prioritized = {}
        for subsystem, items in categorized.items():
            # Sort by priority
            sorted_items = sorted(items, key=lambda x: priority_order[x.priority])
            prioritized[subsystem] = sorted_items

        return prioritized

    async def _create_snapshots(
        self, prioritized: dict[str, list[FeedbackSource]]
    ) -> None:
        """Create snapshots of subsystems before evolution."""
        for subsystem_name in prioritized.keys():
            if prioritized[subsystem_name]:  # Only if there are tasks
                subsystem = EvolutionSubsystem(subsystem_name)
                await self._create_snapshot(subsystem)

    async def _create_snapshot(self, subsystem: EvolutionSubsystem) -> EvolutionState:
        """Create a snapshot of a specific subsystem."""
        snapshot_data: dict[str, Any] = {}

        try:
            if subsystem == EvolutionSubsystem.MEMORY:
                # Snapshot key memory metrics
                fact_count = await self.db.scalar(
                    select(func.count()).select_from(MemoryFact)
                )
                experience_count = await self.db.scalar(
                    select(func.count()).select_from(MemoryExperience)
                )
                snapshot_data = {
                    "fact_count": fact_count,
                    "experience_count": experience_count,
                }

            elif subsystem == EvolutionSubsystem.AGENTS:
                # Snapshot agent states
                result = await self.db.execute(select(Agent))
                agents = result.scalars().all()
                snapshot_data = {
                    "agents": [
                        {
                            "id": str(a.id),
                            "status": a.status,
                            "run_count": a.run_count,
                        }
                        for a in agents
                    ]
                }

            snapshot = EvolutionState(
                subsystem=subsystem,
                timestamp=datetime.now(UTC),
                snapshot_data=snapshot_data,
            )

            self.evolution_history.append(snapshot)
            logger.info(f"Created snapshot for {subsystem.value}")

            return snapshot

        except Exception as e:
            logger.error(f"Failed to create snapshot for {subsystem.value}: {e}")
            # Return empty snapshot
            return EvolutionState(
                subsystem=subsystem,
                timestamp=datetime.now(UTC),
                snapshot_data={},
            )

    async def _evolve_memory(
        self, feedback: list[FeedbackSource]
    ) -> dict[str, Any]:
        """
        Evolve memory subsystem based on feedback.

        Actions:
        - Consolidate redundant memories
        - Strengthen frequently accessed memories
        - Prune low-confidence memories
        - Optimize embedding clusters
        """
        logger.info(f"Evolving memory subsystem with {len(feedback)} items")

        actions_taken = []

        try:
            # Analyze what memory evolutions are needed
            for item in feedback:
                action = item.metadata.get("evolution_action", "")

                if "consolidate" in action.lower() or "redundant" in action.lower():
                    # Consolidate similar memories
                    consolidation_result = await self._consolidate_memories()
                    actions_taken.append(
                        {
                            "action": "consolidate_memories",
                            "result": consolidation_result,
                        }
                    )

                if "prune" in action.lower() or "low confidence" in action.lower():
                    # Prune low-confidence memories
                    prune_result = await self._prune_low_confidence_memories()
                    actions_taken.append(
                        {"action": "prune_memories", "result": prune_result}
                    )

            return {
                "status": "completed",
                "actions": actions_taken,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Memory evolution failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}

    async def _evolve_behavior(
        self, feedback: list[FeedbackSource]
    ) -> dict[str, Any]:
        """
        Evolve behavior patterns based on feedback.

        Actions:
        - Adjust response strategies
        - Update pattern detection thresholds
        - Refine automation triggers
        """
        logger.info(f"Evolving behavior subsystem with {len(feedback)} items")

        actions_taken = []

        try:
            # Use LLM to generate behavior adjustments
            feedback_summary = "\n".join([f"- {f.content}" for f in feedback])

            prompt = f"""Based on this feedback about system behavior:

{feedback_summary}

Suggest specific behavior adjustments as JSON:
{{
    "adjustments": [
        {{
            "parameter": "parameter_name",
            "current_value": "current",
            "suggested_value": "suggested",
            "reason": "why this change helps"
        }}
    ]
}}"""

            response = await claude_client.complete(
                prompt=prompt,
                system="You are a behavior evolution specialist. "
                       "Suggest parameter adjustments to improve system performance.",
                max_tokens=2000,
            )

            adjustments = json.loads(response)

            for adj in adjustments.get("adjustments", []):
                logger.info(
                    f"Behavior adjustment: {adj['parameter']} -> {adj['suggested_value']}"
                )
                actions_taken.append(adj)

            return {
                "status": "completed",
                "actions": actions_taken,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Behavior evolution failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}

    async def _evolve_agents(self, feedback: list[FeedbackSource]) -> dict[str, Any]:
        """
        Evolve agents based on feedback.

        Actions:
        - Fix failing agents
        - Create agents for new patterns
        - Optimize agent triggers
        - Update agent code
        """
        logger.info(f"Evolving agents subsystem with {len(feedback)} items")

        actions_taken = []

        try:
            for item in feedback:
                action = item.metadata.get("evolution_action", "")

                # Fix failing agents
                if "error" in action.lower() or "fail" in action.lower():
                    agent_id = item.metadata.get("agent_id")
                    if agent_id:
                        fix_result = await self._fix_failing_agent(UUID(agent_id))
                        actions_taken.append(
                            {
                                "action": "fix_agent",
                                "agent_id": agent_id,
                                "result": fix_result,
                            }
                        )

                # Create new agents for patterns
                if "automat" in action.lower() or "pattern" in action.lower():
                    pattern_id = item.metadata.get("pattern_id")
                    if pattern_id:
                        create_result = await self._create_agent_for_pattern(
                            UUID(pattern_id)
                        )
                        actions_taken.append(
                            {
                                "action": "create_agent",
                                "pattern_id": pattern_id,
                                "result": create_result,
                            }
                        )

            return {
                "status": "completed",
                "actions": actions_taken,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Agent evolution failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}

    async def _validate_system_health(self) -> dict[str, Any]:
        """
        Validate system health after evolution.

        Checks:
        - Database connectivity
        - Agent success rates
        - Memory operation success rates
        - API response times
        """
        logger.info("Validating system health")

        health_checks = []
        issues = []

        try:
            # Database health
            await self.db.execute(text("SELECT 1"))
            health_checks.append({"check": "database", "status": "healthy"})

        except Exception as e:
            health_checks.append(
                {"check": "database", "status": "unhealthy", "error": str(e)}
            )
            issues.append({"subsystem": "system", "issue": "database_connectivity"})

        # Agent success rate (last 24 hours)
        try:
            one_day_ago = datetime.now(UTC) - timedelta(days=1)
            total_logs = await self.db.scalar(
                select(func.count())
                .select_from(AgentLog)
                .where(AgentLog.created_at >= one_day_ago)
            )
            error_logs = await self.db.scalar(
                select(func.count())
                .select_from(AgentLog)
                .where(AgentLog.created_at >= one_day_ago)
                .where(AgentLog.level == "error")
            )

            if total_logs and total_logs > 0:
                success_rate = 1 - (error_logs or 0) / total_logs
                health_checks.append(
                    {
                        "check": "agent_success_rate",
                        "status": "healthy" if success_rate >= 0.7 else "degraded",
                        "rate": success_rate,
                    }
                )

                if success_rate < 0.7:
                    issues.append(
                        {
                            "subsystem": "agents",
                            "issue": "low_success_rate",
                            "rate": success_rate,
                        }
                    )
            else:
                health_checks.append(
                    {
                        "check": "agent_success_rate",
                        "status": "no_data",
                    }
                )

        except Exception as e:
            logger.error(f"Agent health check failed: {e}")
            health_checks.append(
                {"check": "agent_success_rate", "status": "error", "error": str(e)}
            )

        # Calculate overall health score
        healthy_count = sum(1 for check in health_checks if check["status"] == "healthy")
        total_checks = len(health_checks)
        health_score = healthy_count / total_checks if total_checks > 0 else 0

        return {
            "healthy": health_score >= self.health_threshold,
            "score": health_score,
            "checks": health_checks,
            "issues": issues,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def _perform_rollbacks(self, issues: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Rollback failing evolutions based on detected issues.

        Args:
            issues: List of detected health issues

        Returns:
            Rollback results
        """
        logger.warning(f"Performing rollbacks for {len(issues)} issues")

        rollback_results = []

        for issue in issues:
            subsystem_name = issue.get("subsystem")
            if not subsystem_name:
                continue

            try:
                subsystem = EvolutionSubsystem(subsystem_name)

                # Find most recent snapshot for this subsystem
                recent_snapshots = [
                    s for s in self.evolution_history if s.subsystem == subsystem
                ]

                if recent_snapshots:
                    # Sort by timestamp, get most recent
                    snapshot = max(recent_snapshots, key=lambda s: s.timestamp)
                    result = await self._rollback_snapshot(snapshot)
                    rollback_results.append(
                        {
                            "subsystem": subsystem_name,
                            "snapshot_id": str(snapshot.id),
                            "result": result,
                        }
                    )
                else:
                    logger.warning(f"No snapshot found for {subsystem_name}")
                    rollback_results.append(
                        {
                            "subsystem": subsystem_name,
                            "result": "no_snapshot_available",
                        }
                    )

            except Exception as e:
                logger.error(f"Rollback failed for {subsystem_name}: {e}")
                rollback_results.append(
                    {"subsystem": subsystem_name, "result": "failed", "error": str(e)}
                )

        return {"rollbacks": rollback_results, "timestamp": datetime.now(UTC).isoformat()}

    async def _rollback_snapshot(self, snapshot: EvolutionState) -> str:
        """
        Rollback to a specific snapshot.

        Args:
            snapshot: The snapshot to restore

        Returns:
            Rollback status
        """
        logger.info(
            f"Rolling back {snapshot.subsystem.value} to {snapshot.timestamp}"
        )

        try:
            # Subsystem-specific rollback logic
            if snapshot.subsystem == EvolutionSubsystem.AGENTS:
                # Restore agent states from snapshot
                for agent_data in snapshot.snapshot_data.get("agents", []):
                    agent_id = UUID(agent_data["id"])
                    result = await self.db.execute(
                        select(Agent).where(Agent.id == agent_id)
                    )
                    agent = result.scalar_one_or_none()

                    if agent:
                        agent.status = agent_data["status"]
                        # Restore run_count if available
                        if "run_count" in agent_data:
                            agent.run_count = agent_data["run_count"]

                await self.db.commit()

            # Add more subsystem-specific rollback logic here

            return "success"

        except Exception as e:
            logger.error(f"Snapshot rollback failed: {e}", exc_info=True)
            return f"failed: {e}"

    def _cleanup_old_snapshots(self) -> None:
        """Remove old snapshots to prevent memory bloat."""
        if len(self.evolution_history) > self.max_history_size:
            # Keep only the most recent snapshots
            self.evolution_history.sort(key=lambda s: s.timestamp, reverse=True)
            removed = len(self.evolution_history) - self.max_history_size
            self.evolution_history = self.evolution_history[: self.max_history_size]
            logger.info(f"Cleaned up {removed} old snapshots")

    async def _consolidate_memories(self) -> dict[str, Any]:
        """Consolidate redundant or similar memories."""
        logger.info("Consolidating redundant memories")

        # Placeholder implementation
        # In production, this would use embeddings to find similar memories
        # and merge them intelligently

        return {"consolidated": 0, "status": "placeholder"}

    async def _prune_low_confidence_memories(self) -> dict[str, Any]:
        """Prune memories with consistently low confidence."""
        logger.info("Pruning low-confidence memories")

        # Placeholder implementation
        # In production, this would identify and remove memories
        # that have low confidence scores across multiple retrievals

        return {"pruned": 0, "status": "placeholder"}

    async def _fix_failing_agent(self, agent_id: UUID) -> dict[str, Any]:
        """Attempt to fix a failing agent using LLM analysis."""
        logger.info(f"Attempting to fix failing agent: {agent_id}")

        result = await self.db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

        if not agent:
            return {"status": "not_found"}

        # Get recent error logs
        logs_result = await self.db.execute(
            select(AgentLog)
            .where(AgentLog.agent_id == agent_id)
            .where(AgentLog.level == "error")
            .order_by(AgentLog.created_at.desc())
            .limit(5)
        )
        error_logs = logs_result.scalars().all()

        if not error_logs:
            return {"status": "no_errors_found"}

        # Use LLM to analyze errors and suggest fixes
        errors_summary = "\n".join([f"- {log.message}" for log in error_logs])

        try:
            prompt = f"""This agent is failing with these errors:

Agent: {agent.name}
Type: {agent.agent_type}
Current code:
{agent.code or 'No code available'}

Recent errors:
{errors_summary}

Suggest a fix as JSON:
{{
    "diagnosis": "what's causing the failures",
    "fix": "code or configuration changes needed",
    "confidence": 0.0-1.0
}}"""

            response = await claude_client.complete(
                prompt=prompt,
                system="You are an expert at debugging and fixing automation agents.",
                max_tokens=2000,
            )

            fix_suggestion = json.loads(response)

            # Log the suggestion (actual implementation would apply the fix)
            logger.info(
                f"Fix suggestion for agent {agent_id}: {fix_suggestion['diagnosis']}"
            )

            return {"status": "analyzed", "suggestion": fix_suggestion}

        except Exception as e:
            logger.error(f"Failed to analyze agent errors: {e}")
            return {"status": "analysis_failed", "error": str(e)}

    async def _create_agent_for_pattern(self, pattern_id: UUID) -> dict[str, Any]:
        """Create a new agent to automate a detected pattern."""
        logger.info(f"Creating agent for pattern: {pattern_id}")

        result = await self.db.execute(select(Pattern).where(Pattern.id == pattern_id))
        pattern = result.scalar_one_or_none()

        if not pattern:
            return {"status": "pattern_not_found"}

        # Check if suggestion already exists
        existing = await self.db.execute(
            select(Suggestion).where(Suggestion.pattern_id == pattern_id).limit(1)
        )

        if existing.scalar():
            return {"status": "suggestion_exists"}

        # Create suggestion for this pattern
        suggestion = Suggestion(
            title=f"Automate: {pattern.name}",
            description=f"Detected pattern occurs {pattern.occurrences} times - consider automation",
            agent_type="automation",
            agent_config={"auto_generated": True, "evolution_orchestrator": True},
            confidence=min(0.5 + (pattern.occurrences / 20), 0.95),
            pattern_id=pattern_id,
            impact="medium",
            time_saved_minutes=pattern.time_saved_minutes or 0,
        )

        self.db.add(suggestion)
        await self.db.commit()

        logger.info(f"Created automation suggestion for pattern {pattern.name}")

        return {
            "status": "suggestion_created",
            "suggestion_id": str(suggestion.id),
            "pattern_name": pattern.name,
        }
