"""Agent Evolution System - Auto-creates and improves agents based on patterns and performance."""

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.claude import claude_client
from src.db.models import Agent, AgentLog, Pattern

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Get current UTC time as naive datetime for database compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


class AgentEvolution:
    """
    Autonomous agent evolution system that:
    1. Auto-creates agents from detected patterns
    2. Self-improves underperforming agents
    3. Creates new tools/actions when needed
    4. Deactivates ineffective agents
    """

    # Evolution thresholds
    CONFIDENCE_THRESHOLD = 0.85
    MIN_OCCURRENCES = 5
    RECENCY_DAYS = 7
    SUCCESS_RATE_MIN = 0.7
    MIN_RUNS_FOR_ANALYSIS = 10

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._evolution_history: list[dict[str, Any]] = []
        logger.info("AgentEvolution system initialized")

    async def evolve(self, issues: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """
        Main evolution cycle - orchestrates all evolution activities.

        Args:
            issues: Optional list of user-reported issues to guide evolution

        Returns:
            Summary of evolution actions taken
        """
        logger.info("Starting evolution cycle")
        results: dict[str, Any] = {
            "created_agents": [],
            "improved_agents": [],
            "created_tools": [],
            "deactivated_agents": [],
            "timestamp": _utc_now().isoformat(),
        }

        try:
            # Step 1: Auto-create agents from patterns
            created = await self._auto_create_from_patterns()
            results["created_agents"] = created
            logger.info(f"Auto-created {len(created)} agents from patterns")

            # Step 2: Self-improve underperforming agents
            improved = await self._self_improve_agents()
            results["improved_agents"] = improved
            logger.info(f"Improved {len(improved)} underperforming agents")

            # Step 3: Analyze tool gaps and create new tools if needed
            if issues:
                tool_gaps = await self._analyze_tool_gaps(issues)
                if tool_gaps:
                    created_tools = await self._create_tools(tool_gaps)
                    results["created_tools"] = created_tools
                    logger.info(f"Created {len(created_tools)} new tools")

            # Step 4: Deactivate consistently failing agents
            deactivated = await self._deactivate_failing_agents()
            results["deactivated_agents"] = deactivated
            logger.info(f"Deactivated {len(deactivated)} failing agents")

            # Record evolution
            self._evolution_history.append(results)

            logger.info("Evolution cycle completed successfully")
            return results

        except Exception as e:
            logger.error(f"Evolution cycle failed: {e}", exc_info=True)
            results["error"] = str(e)
            return results

    async def _auto_create_from_patterns(self) -> list[dict[str, Any]]:
        """
        Find qualifying patterns and automatically create agents from them.

        Returns:
            List of created agent summaries
        """
        logger.debug("Analyzing patterns for agent creation")

        # Query patterns that meet criteria for agent creation
        cutoff_date = _utc_now() - timedelta(days=self.RECENCY_DAYS)
        query = (
            select(Pattern)
            .where(
                Pattern.status == "active",
                Pattern.automatable == True,  # noqa: E712
                Pattern.occurrences >= self.MIN_OCCURRENCES,
                Pattern.last_seen_at >= cutoff_date,
            )
            .order_by(Pattern.occurrences.desc())
        )

        result = await self.db.execute(query)
        qualifying_patterns = list(result.scalars().all())

        logger.info(f"Found {len(qualifying_patterns)} qualifying patterns for agent creation")

        created_agents = []
        for pattern in qualifying_patterns:
            # Check if agent already exists for this pattern
            existing_query = select(Agent).where(
                Agent.name.like(f"%{pattern.name}%"),
                Agent.status != "deleted",
            )
            existing_result = await self.db.execute(existing_query)
            if existing_result.scalar_one_or_none():
                logger.debug(f"Agent already exists for pattern: {pattern.name}")
                continue

            try:
                agent = await self._create_agent_from_pattern(pattern)
                created_agents.append({
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "pattern_id": str(pattern.id),
                    "pattern_name": pattern.name,
                })
                logger.info(f"Created agent '{agent.name}' from pattern '{pattern.name}'")
            except Exception as e:
                logger.error(f"Failed to create agent from pattern {pattern.id}: {e}")

        return created_agents

    async def _create_agent_from_pattern(self, pattern: Pattern) -> Agent:
        """
        Use Claude to generate agent configuration from a pattern.

        Args:
            pattern: Pattern to create agent from

        Returns:
            Created Agent instance
        """
        logger.debug(f"Generating agent from pattern: {pattern.name}")

        # Prepare pattern data for Claude
        pattern_data = {
            "name": pattern.name,
            "type": pattern.pattern_type,
            "trigger_conditions": pattern.trigger_conditions,
            "sequence": pattern.sequence,
            "occurrences": pattern.occurrences,
            "avg_duration": pattern.avg_duration_seconds,
        }

        # Ask Claude to generate agent configuration
        prompt = f"""Analyze this user behavior pattern and generate an automation agent configuration:

Pattern Data:
{json.dumps(pattern_data, indent=2)}

Generate a JSON configuration with the following structure:
{{
  "name": "Descriptive agent name",
  "description": "What this agent automates and why",
  "agent_type": "time_based|event_based|sequence_based",
  "trigger_config": {{
    "type": "time|event|sequence",
    "condition": "Specific trigger condition"
  }},
  "actions": [
    {{
      "type": "action_type",
      "target": "what to act on",
      "params": {{}},
      "order": 1
    }}
  ],
  "settings": {{
    "confidence_threshold": 0.8,
    "retry_count": 3,
    "timeout_seconds": 30
  }}
}}

Ensure actions are safe, reversible, and match the pattern's context."""

        try:
            response = await claude_client.complete(
                prompt=prompt,
                system=(
                    "You are an expert in automation and agent design. "
                    "Generate practical, safe, and efficient agent configurations. "
                    "Always respond with valid JSON only, no additional text."
                ),
                max_tokens=2048,
            )

            # Parse Claude's response
            config = json.loads(response)

            # Create agent in database
            agent = Agent(
                name=config["name"],
                description=config["description"],
                agent_type=config["agent_type"],
                trigger_config=config["trigger_config"],
                actions=config["actions"],
                settings=config.get("settings", {}),
                status="draft",  # Start as draft for safety
            )
            self.db.add(agent)
            await self.db.commit()
            await self.db.refresh(agent)

            # Log creation
            log = AgentLog(
                agent_id=agent.id,
                level="info",
                message=f"Auto-created from pattern: {pattern.name}",
                data={"pattern_id": str(pattern.id), "evolution": True},
            )
            self.db.add(log)
            await self.db.commit()

            return agent

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create agent from pattern: {e}")
            raise

    async def _self_improve_agents(self) -> list[dict[str, Any]]:
        """
        Analyze and improve underperforming agents based on their failure patterns.

        Returns:
            List of improved agent summaries
        """
        logger.debug("Analyzing agents for improvement opportunities")

        # Find agents with enough runs to analyze
        query = (
            select(Agent)
            .where(
                Agent.status.in_(["active", "draft"]),
                Agent.run_count >= self.MIN_RUNS_FOR_ANALYSIS,
            )
            .order_by(Agent.run_count.desc())
        )

        result = await self.db.execute(query)
        agents = list(result.scalars().all())

        logger.info(f"Analyzing {len(agents)} agents for improvement")

        improved_agents = []
        for agent in agents:
            # Calculate success rate
            success_rate = (
                agent.success_count / agent.run_count
                if agent.run_count > 0
                else 0
            )

            # Check if agent needs improvement
            if success_rate < self.SUCCESS_RATE_MIN:
                try:
                    improvement_result = await self._improve_agent(agent)
                    improved_agents.append({
                        "agent_id": str(agent.id),
                        "agent_name": agent.name,
                        "old_success_rate": round(success_rate, 3),
                        "improvements": improvement_result,
                    })
                    logger.info(
                        f"Improved agent '{agent.name}' "
                        f"(success rate: {success_rate:.2%})"
                    )
                except Exception as e:
                    logger.error(f"Failed to improve agent {agent.id}: {e}")

        return improved_agents

    async def _improve_agent(self, agent: Agent) -> dict[str, Any]:
        """
        Improve a specific agent based on its failure patterns.

        Args:
            agent: Agent to improve

        Returns:
            Dict describing improvements made
        """
        logger.debug(f"Improving agent: {agent.name}")

        # Get recent error logs
        log_query = (
            select(AgentLog)
            .where(
                AgentLog.agent_id == agent.id,
                AgentLog.level == "error",
            )
            .order_by(AgentLog.created_at.desc())
            .limit(50)
        )
        log_result = await self.db.execute(log_query)
        error_logs = list(log_result.scalars().all())

        # Analyze error patterns
        error_summary: dict[str | None, int] = defaultdict(int)
        for log in error_logs:
            error_summary[log.message] += 1

        # Prepare data for Claude
        agent_data = {
            "name": agent.name,
            "type": agent.agent_type,
            "trigger_config": agent.trigger_config,
            "actions": agent.actions,
            "settings": agent.settings,
            "statistics": {
                "run_count": agent.run_count,
                "success_count": agent.success_count,
                "error_count": agent.error_count,
                "success_rate": agent.success_count / agent.run_count if agent.run_count > 0 else 0,
            },
            "common_errors": dict(error_summary),
        }

        # Ask Claude for improvements
        prompt = f"""Analyze this underperforming automation agent and suggest improvements:

Agent Data:
{json.dumps(agent_data, indent=2)}

Generate a JSON response with:
{{
  "diagnosis": "What's causing the failures",
  "improvements": {{
    "trigger_config": {{}},  # Updated trigger config (if needed)
    "actions": [],  # Updated actions array (if needed)
    "settings": {{}}  # Updated settings (if needed)
  }},
  "reasoning": "Why these changes will improve performance"
}}

Focus on:
1. Making triggers more reliable
2. Adding error handling
3. Adjusting timeouts and retries
4. Fixing action sequencing issues"""

        try:
            response = await claude_client.complete(
                prompt=prompt,
                system=(
                    "You are an expert in debugging and optimizing automation agents. "
                    "Provide practical, tested improvements. "
                    "Always respond with valid JSON only."
                ),
                max_tokens=2048,
            )

            improvement_plan = json.loads(response)

            # Apply improvements
            improvements = improvement_plan.get("improvements", {})
            if improvements.get("trigger_config"):
                agent.trigger_config = improvements["trigger_config"]
            if improvements.get("actions"):
                agent.actions = improvements["actions"]
            if improvements.get("settings"):
                agent.settings.update(improvements["settings"])

            agent.updated_at = datetime.now(UTC).replace(tzinfo=None)
            await self.db.commit()

            # Log improvement
            log = AgentLog(
                agent_id=agent.id,
                level="info",
                message="Agent improved by evolution system",
                data={
                    "diagnosis": improvement_plan.get("diagnosis"),
                    "reasoning": improvement_plan.get("reasoning"),
                    "evolution": True,
                },
            )
            self.db.add(log)
            await self.db.commit()

            return improvement_plan

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse improvement plan: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to improve agent: {e}")
            raise

    async def _analyze_tool_gaps(self, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Identify missing capabilities from user issues.

        Args:
            issues: List of user-reported issues

        Returns:
            List of identified tool gaps
        """
        logger.debug(f"Analyzing {len(issues)} issues for tool gaps")

        # Prepare issues summary for Claude
        prompt = f"""Analyze these user issues and identify missing automation capabilities:

Issues:
{json.dumps(issues, indent=2)}

Generate a JSON array of missing tools/capabilities:
[
  {{
    "capability": "What's missing",
    "use_cases": ["Use case 1", "Use case 2"],
    "priority": "high|medium|low",
    "complexity": "simple|medium|complex"
  }}
]

Focus on:
1. Capabilities users are requesting
2. Common pain points
3. Gaps in current automation coverage"""

        try:
            response = await claude_client.complete(
                prompt=prompt,
                system=(
                    "You are an expert in capability analysis and tool design. "
                    "Identify practical, high-value automation opportunities. "
                    "Always respond with valid JSON only."
                ),
                max_tokens=2048,
            )

            tool_gaps = json.loads(response)
            logger.info(f"Identified {len(tool_gaps)} tool gaps")
            return tool_gaps

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tool gaps response: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to analyze tool gaps: {e}")
            return []

    async def _create_tools(self, tool_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Create new tools to fill identified capability gaps.

        Args:
            tool_gaps: List of identified capability gaps

        Returns:
            List of created tool summaries
        """
        logger.debug(f"Creating tools for {len(tool_gaps)} gaps")

        created_tools = []
        for gap in tool_gaps:
            if gap.get("priority") not in ["high", "medium"]:
                continue

            try:
                # Ask Claude to generate tool specification
                prompt = f"""Design a new automation tool for this capability:

Capability: {gap['capability']}
Use Cases: {gap['use_cases']}
Complexity: {gap['complexity']}

Generate a JSON specification:
{{
  "name": "Tool name",
  "description": "What it does",
  "parameters": [
    {{
      "name": "param_name",
      "type": "string|number|boolean|object",
      "required": true,
      "description": "Parameter description"
    }}
  ],
  "implementation_notes": "How to implement this tool",
  "example_usage": "Example of using this tool"
}}"""

                response = await claude_client.complete(
                    prompt=prompt,
                    system=(
                        "You are an expert in API and tool design. "
                        "Create practical, well-documented tool specifications. "
                        "Always respond with valid JSON only."
                    ),
                    max_tokens=1536,
                )

                tool_spec = json.loads(response)
                created_tools.append({
                    "capability": gap["capability"],
                    "specification": tool_spec,
                })
                logger.info(f"Created tool specification: {tool_spec['name']}")

            except Exception as e:
                logger.error(f"Failed to create tool for gap '{gap['capability']}': {e}")

        return created_tools

    async def _deactivate_failing_agents(self) -> list[dict[str, Any]]:
        """
        Deactivate agents that consistently fail and can't be improved.

        Returns:
            List of deactivated agent summaries
        """
        logger.debug("Checking for agents to deactivate")

        # Find agents with very low success rates and many runs
        query = (
            select(Agent)
            .where(
                Agent.status == "active",
                Agent.run_count >= self.MIN_RUNS_FOR_ANALYSIS * 2,
            )
        )

        result = await self.db.execute(query)
        agents = list(result.scalars().all())

        deactivated_agents = []
        for agent in agents:
            success_rate = (
                agent.success_count / agent.run_count
                if agent.run_count > 0
                else 0
            )

            # Deactivate if success rate is critically low
            if success_rate < (self.SUCCESS_RATE_MIN * 0.5):  # 35% threshold
                logger.warning(
                    f"Deactivating agent '{agent.name}' "
                    f"(success rate: {success_rate:.2%})"
                )

                agent.status = "disabled"
                agent.updated_at = datetime.now(UTC).replace(tzinfo=None)

                # Log deactivation
                log = AgentLog(
                    agent_id=agent.id,
                    level="warning",
                    message="Agent deactivated due to low success rate",
                    data={
                        "success_rate": round(success_rate, 3),
                        "run_count": agent.run_count,
                        "evolution": True,
                    },
                )
                self.db.add(log)

                deactivated_agents.append({
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "success_rate": round(success_rate, 3),
                    "run_count": agent.run_count,
                })

        await self.db.commit()
        logger.info(f"Deactivated {len(deactivated_agents)} failing agents")

        return deactivated_agents

    async def rollback(self, steps: int = 1) -> dict[str, Any]:
        """
        Rollback recent evolution changes.

        Args:
            steps: Number of evolution cycles to rollback

        Returns:
            Summary of rollback actions
        """
        logger.warning(f"Rolling back {steps} evolution cycle(s)")

        if not self._evolution_history:
            return {"error": "No evolution history to rollback"}

        rollback_results: dict[str, Any] = {
            "rolled_back_cycles": 0,
            "agents_deleted": [],
            "agents_restored": [],
            "timestamp": _utc_now().isoformat(),
        }

        try:
            # Get cycles to rollback
            cycles_to_rollback = self._evolution_history[-steps:]

            for cycle in reversed(cycles_to_rollback):
                # Delete created agents
                for agent_info in cycle.get("created_agents", []):
                    agent_id = UUID(agent_info["agent_id"])
                    query = select(Agent).where(Agent.id == agent_id)
                    result = await self.db.execute(query)
                    agent = result.scalar_one_or_none()

                    if agent:
                        self.db.delete(agent)  # delete() is synchronous
                        rollback_results["agents_deleted"].append(str(agent_id))

                # Restore deactivated agents
                for agent_info in cycle.get("deactivated_agents", []):
                    agent_id = UUID(agent_info["agent_id"])
                    query = select(Agent).where(Agent.id == agent_id)
                    result = await self.db.execute(query)
                    agent = result.scalar_one_or_none()

                    if agent:
                        agent.status = "active"
                        agent.updated_at = datetime.now(UTC).replace(tzinfo=None)
                        rollback_results["agents_restored"].append(str(agent_id))

                rollback_results["rolled_back_cycles"] += 1

            await self.db.commit()

            # Remove rolled back cycles from history
            self._evolution_history = self._evolution_history[:-steps]

            logger.info(f"Successfully rolled back {steps} cycle(s)")
            return rollback_results

        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            await self.db.rollback()
            return {"error": str(e)}

    async def get_evolution_stats(self) -> dict[str, Any]:
        """
        Get statistics about the evolution system's performance.

        Returns:
            Evolution statistics
        """
        stats = {
            "total_cycles": len(self._evolution_history),
            "total_agents_created": 0,
            "total_agents_improved": 0,
            "total_tools_created": 0,
            "total_agents_deactivated": 0,
        }

        for cycle in self._evolution_history:
            stats["total_agents_created"] += len(cycle.get("created_agents", []))
            stats["total_agents_improved"] += len(cycle.get("improved_agents", []))
            stats["total_tools_created"] += len(cycle.get("created_tools", []))
            stats["total_agents_deactivated"] += len(cycle.get("deactivated_agents", []))

        # Get current agent performance
        query = select(
            func.count(Agent.id).label("total"),
            func.sum(Agent.success_count).label("total_successes"),
            func.sum(Agent.run_count).label("total_runs"),
        ).where(Agent.status == "active")

        result = await self.db.execute(query)
        row = result.one()

        stats["active_agents"] = row.total or 0
        stats["overall_success_rate"] = (
            round(row.total_successes / row.total_runs, 3)
            if row.total_runs and row.total_runs > 0
            else 0
        )

        return stats
