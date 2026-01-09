"""Tests for Self-Evolving System.

Comprehensive tests for all evolution subsystems:
- Memory Evolution
- Behavior Evolution
- Agent Evolution
- Evolution Orchestrator
- Integration Tests
"""

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import uuid4

import pytest

from src.db.models import Agent, AgentLog, Pattern
from src.db.models.memory import MemoryFact, MemoryOperation
from src.services.evolution.agent_evolution import AgentEvolution
from src.services.evolution.behavior_evolution import BehaviorEvolution
from src.services.evolution.memory_evolution import MemoryEvolution, MemoryParams
from src.services.evolution.orchestrator import (
    EvolutionOrchestrator,
    EvolutionPriority,
    EvolutionSubsystem,
    FeedbackSource,
)


# ===========================================
# FIXTURES
# ===========================================


@pytest.fixture
def db_session():
    """Create a mocked async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.scalar = AsyncMock()
    return session


@pytest.fixture
def temp_params_file(tmp_path):
    """Create a temporary parameters file path."""
    return tmp_path / "memory_params_test.json"


@pytest.fixture
def mock_claude_complete():
    """Mock claude_client.complete function."""
    with patch("src.services.evolution.memory_evolution.claude_client.complete") as mock:
        yield mock


# ===========================================
# TEST MEMORY EVOLUTION
# ===========================================


class TestMemoryEvolution:
    """Test cases for MemoryEvolution service."""

    def test_default_params(self, db_session, temp_params_file):
        """Test that default parameters are loaded correctly."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        assert evolution.current_params.decay_rate_facts == 0.95
        assert evolution.current_params.decay_rate_beliefs == 0.90
        assert evolution.current_params.decay_rate_experiences == 0.85
        assert evolution.current_params.importance_threshold == 0.5
        assert evolution.current_params.link_similarity_threshold == 0.75
        assert evolution.current_params.retrieval_top_k == 10

    def test_adjust_decay_rates_decrease(self, db_session, temp_params_file):
        """Test adjusting decay rates downward (more aggressive pruning)."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        old_facts = evolution.current_params.decay_rate_facts
        old_beliefs = evolution.current_params.decay_rate_beliefs

        changes = evolution._adjust_decay_rates("down")

        assert len(changes) == 3
        assert evolution.current_params.decay_rate_facts < old_facts
        assert evolution.current_params.decay_rate_beliefs < old_beliefs
        assert all("decreased" in change for change in changes)

    def test_adjust_decay_rates_increase(self, db_session, temp_params_file):
        """Test adjusting decay rates upward (longer retention)."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        old_facts = evolution.current_params.decay_rate_facts
        old_beliefs = evolution.current_params.decay_rate_beliefs

        changes = evolution._adjust_decay_rates("up")

        assert len(changes) == 3
        assert evolution.current_params.decay_rate_facts > old_facts
        assert evolution.current_params.decay_rate_beliefs > old_beliefs
        assert all("increased" in change for change in changes)

    @pytest.mark.asyncio
    async def test_rollback(self, db_session, temp_params_file):
        """Test rolling back to previous parameters."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        # Save initial state
        evolution._save_param_history()

        # Modify parameters
        evolution.current_params.decay_rate_facts = 0.80
        evolution._save_params()
        evolution._save_param_history()

        # Rollback
        result = await evolution.rollback()

        assert result["success"] is True
        assert result["restored_params"]["decay_rate_facts"] == 0.95

    @pytest.mark.asyncio
    async def test_evolve_with_forgetting_issues(
        self, db_session, temp_params_file, mock_claude_complete
    ):
        """Test evolution when facts are being forgotten too quickly."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        # Mock LLM response
        mock_claude_complete.return_value = json.dumps([
            {
                "param": "decay_rate_facts",
                "new_value": 0.97,
                "reason": "Increase retention to reduce forgetting",
            }
        ])

        issues = [{"type": "low_recall", "severity": "high", "details": "Users complaining about forgetting"}]

        old_decay = evolution.current_params.decay_rate_facts
        result = await evolution.evolve(issues)

        assert result["changed"] is True
        assert len(result["changes"]) > 0
        assert evolution.current_params.decay_rate_facts >= old_decay

    @pytest.mark.asyncio
    async def test_evolve_memory_overload(
        self, db_session, temp_params_file, mock_claude_complete
    ):
        """Test evolution when memory system is overloaded."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        mock_claude_complete.return_value = json.dumps([])

        issues = [
            {"type": "memory_overload", "severity": "high", "details": "Too many memories"}
        ]

        old_decay = evolution.current_params.decay_rate_facts
        old_threshold = evolution.current_params.importance_threshold

        result = await evolution.evolve(issues)

        assert result["changed"] is True
        # Should decrease decay (more aggressive pruning) and increase threshold
        assert evolution.current_params.decay_rate_facts < old_decay
        assert evolution.current_params.importance_threshold > old_threshold

    @pytest.mark.asyncio
    async def test_evolve_poor_retrieval(
        self, db_session, temp_params_file, mock_claude_complete
    ):
        """Test evolution when retrieval is not finding relevant memories."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        mock_claude_complete.return_value = json.dumps([])

        issues = [{"type": "poor_retrieval", "severity": "medium"}]

        old_k = evolution.current_params.retrieval_top_k
        result = await evolution.evolve(issues)

        assert result["changed"] is True
        assert evolution.current_params.retrieval_top_k > old_k

    @pytest.mark.asyncio
    async def test_evolve_no_issues(self, db_session, temp_params_file):
        """Test that no changes are made when there are no issues."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        result = await evolution.evolve([])

        assert result["changed"] is False
        assert result["message"] == "No issues to address"

    def test_apply_suggestion_valid(self, db_session, temp_params_file):
        """Test applying a valid LLM suggestion."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        suggestion = {
            "param": "decay_rate_facts",
            "new_value": 0.93,
            "reason": "Reduce retention slightly",
        }

        result = evolution._apply_suggestion(suggestion)

        assert result is not None
        assert evolution.current_params.decay_rate_facts == 0.93
        assert "0.95 -> 0.93" in result

    def test_apply_suggestion_invalid_param(self, db_session, temp_params_file):
        """Test that invalid parameter suggestions are rejected."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        suggestion = {"param": "nonexistent_param", "new_value": 0.5, "reason": "Test"}

        result = evolution._apply_suggestion(suggestion)

        assert result is None

    def test_apply_suggestion_out_of_range(self, db_session, temp_params_file):
        """Test that out-of-range values are rejected."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        suggestion = {
            "param": "decay_rate_facts",
            "new_value": 1.5,
            "reason": "Invalid value",
        }

        result = evolution._apply_suggestion(suggestion)

        assert result is None

    @pytest.mark.asyncio
    async def test_reset_to_defaults(self, db_session, temp_params_file):
        """Test resetting parameters to defaults."""
        evolution = MemoryEvolution(db_session, session_id="test", params_file=temp_params_file)

        # Modify parameters
        evolution.current_params.decay_rate_facts = 0.80
        evolution.current_params.importance_threshold = 0.7

        result = await evolution.reset_to_defaults()

        assert result["success"] is True
        assert evolution.current_params.decay_rate_facts == 0.95
        assert evolution.current_params.importance_threshold == 0.5


# ===========================================
# TEST BEHAVIOR EVOLUTION
# ===========================================


class TestBehaviorEvolution:
    """Test cases for BehaviorEvolution service."""

    def test_default_behavior(self, db_session):
        """Test that default behavior parameters are set correctly."""
        evolution = BehaviorEvolution(db_session, session_id="test")

        assert evolution.behavior["verbosity"] == 0.5
        assert evolution.behavior["ask_threshold"] == 0.5
        assert evolution.behavior["formality"] == 0.5
        assert evolution.behavior["proactivity"] == 0.5
        assert evolution.behavior["emoji_usage"] == 0.0
        assert evolution.behavior["code_detail"] == 0.6

    def test_adjust_param_bounds(self, db_session):
        """Test that parameter adjustments are clamped to [0.0, 1.0]."""
        evolution = BehaviorEvolution(db_session, session_id="test")

        # Test upper bound
        evolution._adjust_param("verbosity", 0.8)
        assert evolution.behavior["verbosity"] == 1.0

        # Test lower bound
        evolution._adjust_param("verbosity", -2.0)
        assert evolution.behavior["verbosity"] == 0.0

    def test_behavior_prompt_modifier(self, db_session):
        """Test generating behavior prompt modifiers."""
        evolution = BehaviorEvolution(db_session, session_id="test")

        # Set high verbosity
        evolution.behavior["verbosity"] = 0.9
        modifier = evolution.get_behavior_prompt_modifier()

        assert "detailed, comprehensive" in modifier.lower()
        assert "NEVER use emojis" in modifier

    def test_behavior_prompt_modifier_concise(self, db_session):
        """Test prompt modifier for concise behavior."""
        evolution = BehaviorEvolution(db_session, session_id="test")

        evolution.behavior["verbosity"] = 0.2
        modifier = evolution.get_behavior_prompt_modifier()

        assert "concise" in modifier.lower() or "brief" in modifier.lower()

    @pytest.mark.asyncio
    async def test_evolve_too_long_feedback(self, db_session):
        """Test evolution when user feedback indicates responses are too long."""
        evolution = BehaviorEvolution(db_session, session_id="test")

        # Mock database query for chat messages
        mock_msg1 = MagicMock()
        mock_msg1.role = "user"
        mock_msg1.content = "Please make your responses shorter"
        mock_msg1.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

        mock_msg2 = MagicMock()
        mock_msg2.role = "user"
        mock_msg2.content = "Too verbose, can you be more brief?"
        mock_msg2.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_msg1, mock_msg2]
        db_session.execute = AsyncMock(return_value=mock_result)

        issues = [{"type": "verbosity_complaint", "severity": "medium"}]

        old_verbosity = evolution.behavior["verbosity"]
        result = await evolution.evolve(issues)

        assert evolution.behavior["verbosity"] < old_verbosity

    @pytest.mark.asyncio
    async def test_analyze_recent_chats(self, db_session):
        """Test analyzing recent chat messages for patterns."""
        evolution = BehaviorEvolution(db_session, session_id="test")

        # Mock chat messages
        mock_msg1 = MagicMock()
        mock_msg1.role = "user"
        mock_msg1.content = "Great job, спасибо!"
        mock_msg1.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

        mock_msg2 = MagicMock()
        mock_msg2.role = "user"
        mock_msg2.content = "Please make it shorter"
        mock_msg2.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

        mock_msg3 = MagicMock()
        mock_msg3.role = "assistant"
        mock_msg3.content = "Here is the detailed response..."
        mock_msg3.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_msg1, mock_msg2, mock_msg3]
        db_session.execute = AsyncMock(return_value=mock_result)

        analysis = await evolution._analyze_recent_chats()

        assert analysis["total_messages"] == 3
        assert analysis["user_messages"] == 2
        assert analysis["assistant_messages"] == 1
        assert analysis["positive_feedback_count"] >= 1
        assert analysis["brevity_requests"] >= 1
        assert analysis["russian_usage"] >= 1

    @pytest.mark.asyncio
    async def test_apply_insight_valid(self, db_session):
        """Test applying a valid behavior insight."""
        evolution = BehaviorEvolution(db_session, session_id="test")

        insight = {
            "parameter": "verbosity",
            "adjustment": -0.2,
            "reasoning": "User prefers concise responses",
        }

        old_value = evolution.behavior["verbosity"]
        result = await evolution._apply_insight(insight)

        assert result is not None
        assert evolution.behavior["verbosity"] < old_value
        assert "0.50 to 0.30" in result

    @pytest.mark.asyncio
    async def test_apply_insight_large_adjustment_rejected(self, db_session):
        """Test that large adjustments are rejected for safety."""
        evolution = BehaviorEvolution(db_session, session_id="test")

        insight = {
            "parameter": "verbosity",
            "adjustment": 0.5,  # Too large
            "reasoning": "Test",
        }

        result = await evolution._apply_insight(insight)

        assert result is None

    @pytest.mark.asyncio
    async def test_rollback(self, db_session):
        """Test rolling back behavior changes."""
        evolution = BehaviorEvolution(db_session, session_id="test")

        # Make some changes
        await evolution._save_behavior_history()
        evolution.behavior["verbosity"] = 0.8
        evolution.evolution_count = 1

        await evolution._save_behavior_history()
        evolution.behavior["verbosity"] = 0.9
        evolution.evolution_count = 2

        # Rollback
        result = await evolution.rollback(steps=1)

        assert result["success"] is True
        assert result["steps_rolled_back"] == 1
        assert result["current_behavior"]["verbosity"] == 0.8


# ===========================================
# TEST AGENT EVOLUTION
# ===========================================


class TestAgentEvolution:
    """Test cases for AgentEvolution service."""

    def test_thresholds(self, db_session):
        """Test that evolution thresholds are set correctly."""
        evolution = AgentEvolution(db_session)

        assert evolution.CONFIDENCE_THRESHOLD == 0.85
        assert evolution.MIN_OCCURRENCES == 5
        assert evolution.RECENCY_DAYS == 7
        assert evolution.SUCCESS_RATE_MIN == 0.7
        assert evolution.MIN_RUNS_FOR_ANALYSIS == 10

    @pytest.mark.asyncio
    async def test_analyze_tool_gaps(self, db_session):
        """Test analyzing issues for tool gaps."""
        evolution = AgentEvolution(db_session)

        issues = [
            {
                "type": "missing_capability",
                "description": "Users need email automation",
                "frequency": 10,
            },
            {
                "type": "manual_task",
                "description": "Data export is manual and tedious",
                "frequency": 5,
            },
        ]

        with patch("src.services.evolution.agent_evolution.claude_client.complete") as mock:
            mock.return_value = json.dumps([
                {
                    "capability": "Email automation",
                    "use_cases": ["Send notifications", "Schedule emails"],
                    "priority": "high",
                    "complexity": "medium",
                }
            ])

            tool_gaps = await evolution._analyze_tool_gaps(issues)

            assert len(tool_gaps) >= 1
            assert tool_gaps[0]["capability"] == "Email automation"
            assert tool_gaps[0]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_auto_create_from_patterns(self, db_session):
        """Test automatic agent creation from patterns."""
        evolution = AgentEvolution(db_session)

        # Mock pattern query
        pattern1 = Pattern(
            id=uuid4(),
            name="Daily Status Check",
            pattern_type="time_based",
            status="active",
            automatable=True,
            occurrences=10,
            last_seen_at=datetime.now(UTC),
            frequency=10,
            trigger_conditions={"schedule": "0 9 * * *"},
            sequence=["check_status", "send_notification"],
        )

        mock_pattern_result = MagicMock()
        mock_pattern_result.scalars.return_value.all.return_value = [pattern1]

        # Mock existing agent query (no existing agent)
        mock_agent_result = MagicMock()
        mock_agent_result.scalar_one_or_none.return_value = None

        db_session.execute = AsyncMock(side_effect=[mock_pattern_result, mock_agent_result])

        with patch("src.services.evolution.agent_evolution.claude_client.complete") as mock:
            mock.return_value = json.dumps({
                "name": "Daily Status Agent",
                "description": "Checks status daily",
                "agent_type": "time_based",
                "trigger_config": {"type": "time", "condition": "0 9 * * *"},
                "actions": [{"type": "check_status", "target": "system", "params": {}, "order": 1}],
                "settings": {"confidence_threshold": 0.8},
            })

            created = await evolution._auto_create_from_patterns()

            assert len(created) == 1
            assert created[0]["pattern_name"] == "Daily Status Check"

    @pytest.mark.asyncio
    async def test_self_improve_agents(self, db_session):
        """Test self-improvement of underperforming agents."""
        evolution = AgentEvolution(db_session)

        # Mock agent with low success rate
        agent = Agent(
            id=uuid4(),
            name="Failing Agent",
            agent_type="monitor",
            status="active",
            run_count=20,
            success_count=10,  # 50% success rate (below 70% threshold)
            error_count=10,
            trigger_config={},
            actions=[],
            settings={},
            version=1,
        )

        mock_agent_result = MagicMock()
        mock_agent_result.scalars.return_value.all.return_value = [agent]
        db_session.execute = AsyncMock(return_value=mock_agent_result)

        # Mock error logs
        error_log = AgentLog(
            id=uuid4(),
            agent_id=agent.id,
            level="error",
            status="error",
            message="Connection timeout",
            error="Timeout after 30s",
            executed_at=datetime.now(UTC),
        )

        mock_log_result = MagicMock()
        mock_log_result.scalars.return_value.all.return_value = [error_log]

        with patch("src.services.evolution.agent_evolution.claude_client.complete") as mock:
            mock.return_value = json.dumps({
                "diagnosis": "Connection timeouts due to short timeout setting",
                "improvements": {
                    "settings": {"timeout_seconds": 60}
                },
                "reasoning": "Increase timeout to handle slower responses",
            })

            db_session.execute = AsyncMock(side_effect=[mock_agent_result, mock_log_result])

            improved = await evolution._self_improve_agents()

            assert len(improved) == 1
            assert improved[0]["agent_name"] == "Failing Agent"
            assert improved[0]["old_success_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_deactivate_failing_agents(self, db_session):
        """Test deactivation of consistently failing agents."""
        evolution = AgentEvolution(db_session)

        # Mock agent with very low success rate
        agent = Agent(
            id=uuid4(),
            name="Critically Failing Agent",
            agent_type="monitor",
            status="active",
            run_count=30,
            success_count=5,  # ~17% success rate
            error_count=25,
            trigger_config={},
            actions=[],
            settings={},
            version=1,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [agent]
        db_session.execute = AsyncMock(return_value=mock_result)

        deactivated = await evolution._deactivate_failing_agents()

        assert len(deactivated) == 1
        assert deactivated[0]["agent_name"] == "Critically Failing Agent"
        assert agent.status == "disabled"


# ===========================================
# TEST EVOLUTION ORCHESTRATOR
# ===========================================


class TestEvolutionOrchestrator:
    """Test cases for EvolutionOrchestrator."""

    @pytest.mark.asyncio
    async def test_analyze_feedback_categorization(self, db_session):
        """Test that feedback is correctly categorized by subsystem."""
        orchestrator = EvolutionOrchestrator(db_session)

        feedback = [
            FeedbackSource(
                source_type="user_complaint",
                priority=EvolutionPriority.HIGH,
                subsystem=EvolutionSubsystem.MEMORY,
                content="Memory recall is poor",
            ),
            FeedbackSource(
                source_type="agent_error",
                priority=EvolutionPriority.CRITICAL,
                subsystem=EvolutionSubsystem.AGENTS,
                content="Agent execution failed",
            ),
            FeedbackSource(
                source_type="behavior_feedback",
                priority=EvolutionPriority.MEDIUM,
                subsystem=EvolutionSubsystem.BEHAVIOR,
                content="Responses are too long",
            ),
        ]

        with patch("src.services.evolution.orchestrator.claude_client.complete") as mock:
            mock.return_value = json.dumps({
                "categorized_feedback": [
                    {
                        "id": str(feedback[0].id),
                        "subsystem": "memory",
                        "priority": "high",
                        "action": "Consolidate similar memories",
                    },
                    {
                        "id": str(feedback[1].id),
                        "subsystem": "agents",
                        "priority": "critical",
                        "action": "Fix failing agent",
                    },
                    {
                        "id": str(feedback[2].id),
                        "subsystem": "behavior",
                        "priority": "medium",
                        "action": "Reduce verbosity",
                    },
                ]
            })

            categorized = await orchestrator._analyze_feedback(feedback)

            assert len(categorized["memory"]) == 1
            assert len(categorized["agents"]) == 1
            assert len(categorized["behavior"]) == 1

    @pytest.mark.asyncio
    async def test_validate_system_health(self, db_session):
        """Test system health validation."""
        orchestrator = EvolutionOrchestrator(db_session)

        # Mock successful database check
        db_session.execute = AsyncMock()
        db_session.scalar = AsyncMock(side_effect=[100, 10])  # 100 total, 10 errors = 90% success

        health = await orchestrator._validate_system_health()

        assert "healthy" in health
        assert health["score"] >= 0.7
        assert len(health["checks"]) > 0

    @pytest.mark.asyncio
    async def test_validate_system_health_degraded(self, db_session):
        """Test system health validation when health is degraded."""
        orchestrator = EvolutionOrchestrator(db_session)

        # Mock database check failure
        db_session.execute = AsyncMock(side_effect=Exception("DB Error"))

        health = await orchestrator._validate_system_health()

        assert health["healthy"] is False
        assert len(health["issues"]) > 0

    @pytest.mark.asyncio
    async def test_collect_agent_feedback(self, db_session):
        """Test collecting feedback from agent logs."""
        orchestrator = EvolutionOrchestrator(db_session)

        # Mock agent error logs
        error_log = AgentLog(
            id=uuid4(),
            agent_id=uuid4(),
            level="error",
            status="error",
            message="Agent failed",
            error="Connection refused",
            executed_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [error_log]
        db_session.execute = AsyncMock(return_value=mock_result)

        feedback = await orchestrator._collect_agent_feedback()

        assert len(feedback) == 1
        assert feedback[0].subsystem == EvolutionSubsystem.AGENTS
        assert feedback[0].priority == EvolutionPriority.HIGH

    @pytest.mark.asyncio
    async def test_collect_memory_feedback(self, db_session):
        """Test collecting feedback from memory operations."""
        orchestrator = EvolutionOrchestrator(db_session)

        # Mock memory operations with low confidence
        operations = [
            MagicMock(metadata={"confidence": 0.3}),
            MagicMock(metadata={"confidence": 0.4}),
            MagicMock(metadata={"confidence": 0.45}),
            MagicMock(metadata={"confidence": 0.35}),
            MagicMock(metadata={"confidence": 0.4}),
            MagicMock(metadata={"confidence": 0.3}),
            MagicMock(metadata={"confidence": 0.45}),
            MagicMock(metadata={"confidence": 0.4}),
            MagicMock(metadata={"confidence": 0.3}),
            MagicMock(metadata={"confidence": 0.35}),
            MagicMock(metadata={"confidence": 0.4}),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = operations
        db_session.execute = AsyncMock(return_value=mock_result)

        feedback = await orchestrator._collect_memory_feedback()

        # Should detect high number of low-confidence operations
        assert len(feedback) >= 1
        assert feedback[0].subsystem == EvolutionSubsystem.MEMORY

    @pytest.mark.asyncio
    async def test_evolve_memory(self, db_session):
        """Test memory subsystem evolution."""
        orchestrator = EvolutionOrchestrator(db_session)

        feedback = [
            FeedbackSource(
                source_type="memory_issue",
                priority=EvolutionPriority.HIGH,
                subsystem=EvolutionSubsystem.MEMORY,
                content="Low confidence operations",
                metadata={"evolution_action": "prune low confidence memories"},
            )
        ]

        result = await orchestrator._evolve_memory(feedback)

        assert result["status"] == "completed"
        assert "actions" in result

    @pytest.mark.asyncio
    async def test_evolve_behavior(self, db_session):
        """Test behavior subsystem evolution."""
        orchestrator = EvolutionOrchestrator(db_session)

        feedback = [
            FeedbackSource(
                source_type="user_feedback",
                priority=EvolutionPriority.MEDIUM,
                subsystem=EvolutionSubsystem.BEHAVIOR,
                content="Responses are too verbose",
            )
        ]

        with patch("src.services.evolution.orchestrator.claude_client.complete") as mock:
            mock.return_value = json.dumps({
                "adjustments": [
                    {
                        "parameter": "verbosity",
                        "current_value": "0.7",
                        "suggested_value": "0.5",
                        "reason": "User prefers shorter responses",
                    }
                ]
            })

            result = await orchestrator._evolve_behavior(feedback)

            assert result["status"] == "completed"
            assert len(result["actions"]) >= 1

    @pytest.mark.asyncio
    async def test_trigger_immediate_evolution(self, db_session):
        """Test triggering immediate evolution for critical issues."""
        orchestrator = EvolutionOrchestrator(db_session)

        # Mock database checks for health validation
        db_session.execute = AsyncMock()
        db_session.scalar = AsyncMock(side_effect=[100, 5])  # High success rate

        with patch("src.services.evolution.orchestrator.claude_client.complete") as mock:
            mock.return_value = json.dumps({"adjustments": []})

            result = await orchestrator.trigger_immediate_evolution(
                subsystem=EvolutionSubsystem.BEHAVIOR,
                reason="Critical user complaint about response length",
                metadata={"user_id": "test123"},
            )

            assert "status" in result


# ===========================================
# TEST INTEGRATION
# ===========================================


class TestIntegration:
    """Integration tests for the complete evolution cycle."""

    @pytest.mark.asyncio
    async def test_full_evolution_cycle(self, db_session):
        """Test a complete evolution cycle with mocked Claude API."""
        orchestrator = EvolutionOrchestrator(db_session)

        # Mock all database queries
        # Agent logs
        mock_agent_log = AgentLog(
            id=uuid4(),
            agent_id=uuid4(),
            level="error",
            status="error",
            message="Test error",
            error="Test error details",
            executed_at=datetime.now(UTC),
        )

        # Memory operations
        mock_memory_ops = [
            MagicMock(metadata={"confidence": 0.9}),
            MagicMock(metadata={"confidence": 0.8}),
        ]

        # Patterns
        mock_pattern = Pattern(
            id=uuid4(),
            name="Test Pattern",
            pattern_type="time_based",
            status="active",
            frequency=5,
        )

        # Setup mock returns for different queries
        mock_log_result = MagicMock()
        mock_log_result.scalars.return_value.all.return_value = [mock_agent_log]

        mock_memory_result = MagicMock()
        mock_memory_result.scalars.return_value.all.return_value = mock_memory_ops

        mock_pattern_result = MagicMock()
        mock_pattern_result.scalars.return_value.all.return_value = [mock_pattern]

        mock_agent_check = MagicMock()
        mock_agent_check.scalar.return_value = None

        mock_health_check = MagicMock()

        db_session.execute = AsyncMock(
            side_effect=[
                mock_log_result,  # Agent logs
                mock_memory_result,  # Memory operations
                mock_health_check,  # System health check
                mock_pattern_result,  # Pattern check
                mock_agent_check,  # Agent exists check
                mock_health_check,  # Final health validation
                mock_health_check,  # Agent success rate check
            ]
        )

        db_session.scalar = AsyncMock(side_effect=[100, 10, 0, 0])  # Health check counts

        # Mock Claude API calls
        with patch("src.services.evolution.orchestrator.claude_client.complete") as mock_complete:
            # Mock feedback analysis
            mock_complete.side_effect = [
                json.dumps({
                    "categorized_feedback": [
                        {
                            "id": "test-id",
                            "subsystem": "agents",
                            "priority": "high",
                            "action": "Fix failing agent",
                        }
                    ]
                }),
                json.dumps({"adjustments": []}),  # Behavior evolution
            ]

            result = await orchestrator.run_evolution_cycle()

            assert result["status"] == "completed"
            assert "feedback_collected" in result
            assert "evolutions_performed" in result
            assert "health_check" in result

    @pytest.mark.asyncio
    async def test_evolution_with_rollback(self, db_session):
        """Test that evolution rolls back when health degrades."""
        orchestrator = EvolutionOrchestrator(db_session)
        orchestrator.health_threshold = 0.8

        # Setup mock for initial feedback collection
        db_session.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        ))

        # Mock Claude API
        with patch("src.services.evolution.orchestrator.claude_client.complete") as mock:
            mock.return_value = json.dumps({"categorized_feedback": []})

            # Mock health check to return degraded health
            with patch.object(orchestrator, "_validate_system_health") as mock_health:
                mock_health.return_value = {
                    "healthy": False,
                    "score": 0.5,
                    "checks": [],
                    "issues": [{"subsystem": "agents", "issue": "low_success_rate"}],
                }

                result = await orchestrator.run_evolution_cycle()

                # Should have performed rollbacks
                assert "rollbacks" in result["evolutions_performed"]

    @pytest.mark.asyncio
    async def test_memory_behavior_integration(self, db_session, temp_params_file):
        """Test integration between memory and behavior evolution."""
        memory_evolution = MemoryEvolution(
            db_session, session_id="test", params_file=temp_params_file
        )
        behavior_evolution = BehaviorEvolution(db_session, session_id="test")

        # Simulate user feedback about memory and behavior
        memory_issues = [
            {"type": "low_recall", "severity": "high"},
            {"type": "poor_retrieval", "severity": "medium"},
        ]

        behavior_issues = [
            {"type": "verbosity_complaint", "severity": "medium"},
        ]

        with patch("src.services.evolution.memory_evolution.claude_client.complete") as mock1:
            mock1.return_value = json.dumps([])

            # Mock database for behavior evolution
            mock_msg = MagicMock()
            mock_msg.role = "user"
            mock_msg.content = "Too verbose"
            mock_msg.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_msg]
            db_session.execute = AsyncMock(return_value=mock_result)

            with patch("src.services.evolution.behavior_evolution.claude_client.complete") as mock2:
                mock2.return_value = json.dumps([])

                # Run both evolutions
                memory_result = await memory_evolution.evolve(memory_issues)
                behavior_result = await behavior_evolution.evolve(behavior_issues)

                # Both should have made changes
                assert memory_result["changed"] is True
                assert "changes" in behavior_result

    @pytest.mark.asyncio
    async def test_evolution_history_management(self, db_session):
        """Test that evolution history is properly managed."""
        orchestrator = EvolutionOrchestrator(db_session)
        orchestrator.max_history_size = 5

        # Create snapshots beyond max size
        for i in range(10):
            snapshot = MagicMock()
            snapshot.timestamp = datetime.now(UTC) - timedelta(hours=i)
            orchestrator.evolution_history.append(snapshot)

        # Cleanup should reduce to max size
        orchestrator._cleanup_old_snapshots()

        assert len(orchestrator.evolution_history) == 5

    @pytest.mark.asyncio
    async def test_concurrent_evolution_safety(self, db_session, temp_params_file):
        """Test that evolution handles concurrent modifications safely."""
        memory_evolution = MemoryEvolution(
            db_session, session_id="test", params_file=temp_params_file
        )

        # Save initial state
        memory_evolution._save_param_history()

        # Simulate concurrent modifications
        original_decay = memory_evolution.current_params.decay_rate_facts

        issues1 = [{"type": "low_recall", "severity": "high"}]
        issues2 = [{"type": "memory_overload", "severity": "high"}]

        with patch("src.services.evolution.memory_evolution.claude_client.complete") as mock:
            mock.return_value = json.dumps([])

            # Run two evolutions
            await memory_evolution.evolve(issues1)
            await memory_evolution.evolve(issues2)

            # Should be able to rollback
            result = await memory_evolution.rollback()
            assert result["success"] is True
