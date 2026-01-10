"""Memory Evolution Service.

This module evolves memory system parameters based on performance analysis:
- What to remember (importance scoring)
- How long to remember (decay rates)
- How to connect memories (linking strategies)
- How to retrieve (search optimization)
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.claude import claude_client

logger = logging.getLogger(__name__)


@dataclass
class MemoryParams:
    """Memory system parameters."""

    decay_rate_facts: float
    decay_rate_beliefs: float
    decay_rate_experiences: float
    importance_threshold: float
    link_similarity_threshold: float
    retrieval_top_k: int
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MemoryEvolution:
    """Evolves memory system parameters based on performance analysis."""

    DEFAULT_PARAMS: dict[str, float | int | str] = {
        "decay_rate_facts": 0.95,  # Lower decay = longer retention
        "decay_rate_beliefs": 0.90,  # Beliefs decay slower than facts
        "decay_rate_experiences": 0.85,  # Experiences decay fastest
        "importance_threshold": 0.5,  # Minimum importance to keep
        "link_similarity_threshold": 0.75,  # Minimum similarity for linking
        "retrieval_top_k": 10,  # Number of results to retrieve
    }

    def __init__(
        self,
        db: AsyncSession,
        session_id: str = "default",
        params_file: Path | None = None,
    ) -> None:
        """Initialize Memory Evolution service.

        Args:
            db: Database session
            session_id: Session identifier
            params_file: Path to parameters file (defaults to data/memory_params_{session_id}.json)
        """
        self.db = db
        self.session_id = session_id

        if params_file is None:
            data_dir = Path(__file__).parent.parent.parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            params_file = data_dir / f"memory_params_{session_id}.json"

        self.params_file = params_file
        self.history_file = params_file.with_suffix(".history.json")

        self.current_params = self._load_params()
        logger.info(
            f"Memory Evolution initialized for session {session_id}",
            extra={
                "params": self.current_params.to_dict(),
                "params_file": str(self.params_file),
            },
        )

    def _load_params(self) -> MemoryParams:
        """Load parameters from file or use defaults."""
        if self.params_file.exists():
            try:
                with open(self.params_file) as f:
                    data = json.load(f)
                logger.info(f"Loaded memory params from {self.params_file}")
                return MemoryParams(**data)
            except Exception as e:
                logger.error(f"Failed to load params: {e}, using defaults")

        # Use defaults
        params_dict = self.DEFAULT_PARAMS.copy()
        params_dict["updated_at"] = datetime.now(UTC).isoformat()
        return MemoryParams(**params_dict)  # type: ignore

    def _save_params(self) -> None:
        """Save current parameters to file."""
        try:
            with open(self.params_file, "w") as f:
                json.dump(self.current_params.to_dict(), f, indent=2)
            logger.info(f"Saved memory params to {self.params_file}")
        except Exception as e:
            logger.error(f"Failed to save params: {e}")

    def _save_param_history(self) -> None:
        """Save current params to history for rollback."""
        try:
            history: list[dict[str, Any]] = []
            if self.history_file.exists():
                with open(self.history_file) as f:
                    history = json.load(f)

            # Add current params to history
            history.append(self.current_params.to_dict())

            # Keep only last 10 versions
            history = history[-10:]

            with open(self.history_file, "w") as f:
                json.dump(history, f, indent=2)

            logger.info(f"Saved param history (total: {len(history)})")
        except Exception as e:
            logger.error(f"Failed to save param history: {e}")

    async def evolve(self, issues: list[dict[str, Any]]) -> dict[str, Any]:
        """Main evolution method - analyze issues and adjust parameters.

        Args:
            issues: List of detected issues with memory system
                Example: [
                    {"type": "low_recall", "severity": "high", "details": "..."},
                    {"type": "memory_overload", "severity": "medium", "details": "..."}
                ]

        Returns:
            Evolution summary with changes made
        """
        logger.info(
            f"Starting memory evolution with {len(issues)} issues",
            extra={"issues": issues},
        )

        if not issues:
            logger.info("No issues detected, skipping evolution")
            return {"changed": False, "message": "No issues to address"}

        # Save current state for potential rollback
        self._save_param_history()

        changes: list[str] = []

        # Analyze issues and make local adjustments
        for issue in issues:
            issue_type = issue.get("type", "")
            _severity = issue.get("severity", "low")  # noqa: F841

            if issue_type == "low_recall":
                # Facts being forgotten too quickly
                changes.extend(self._adjust_decay_rates("up"))
            elif issue_type == "memory_overload":
                # Too many memories, need more aggressive pruning
                changes.extend(self._adjust_decay_rates("down"))
                changes.extend(self._adjust_importance_threshold("up"))
            elif issue_type == "poor_retrieval":
                # Retrieval not finding relevant memories
                changes.extend(self._adjust_retrieval_params())
            elif issue_type == "weak_connections":
                # Memories not being linked effectively
                changes.extend(self._adjust_link_threshold("down"))
            elif issue_type == "link_noise":
                # Too many weak links
                changes.extend(self._adjust_link_threshold("up"))

        # Get LLM suggestions for more nuanced adjustments
        try:
            suggestions = await self._get_llm_suggestions(issues)
            for suggestion in suggestions:
                applied = self._apply_suggestion(suggestion)
                if applied:
                    changes.append(applied)
        except Exception as e:
            logger.error(f"Failed to get LLM suggestions: {e}")

        # Update timestamp
        self.current_params.updated_at = datetime.now(UTC).isoformat()

        # Save updated params
        self._save_params()

        evolution_summary = {
            "changed": len(changes) > 0,
            "changes": changes,
            "new_params": self.current_params.to_dict(),
            "issues_addressed": len(issues),
        }

        logger.info(
            "Memory evolution complete",
            extra={"summary": evolution_summary},
        )

        return evolution_summary

    def _adjust_decay_rates(self, direction: str) -> list[str]:
        """Adjust decay rates up or down.

        Args:
            direction: "up" to decrease decay (longer retention) or "down" to increase decay

        Returns:
            List of changes made
        """
        changes: list[str] = []
        adjustment = 0.02 if direction == "up" else -0.02

        # Adjust all decay rates
        for param_name in ["decay_rate_facts", "decay_rate_beliefs", "decay_rate_experiences"]:
            old_value = getattr(self.current_params, param_name)
            new_value = max(0.5, min(0.99, old_value + adjustment))

            if new_value != old_value:
                setattr(self.current_params, param_name, new_value)
                changes.append(
                    f"{param_name}: {old_value:.2f} -> {new_value:.2f} "
                    f"({'increased' if direction == 'up' else 'decreased'} retention)"
                )

        return changes

    def _adjust_importance_threshold(self, direction: str) -> list[str]:
        """Adjust importance threshold.

        Args:
            direction: "up" to be more selective or "down" to be less selective

        Returns:
            List of changes made
        """
        changes: list[str] = []
        adjustment = 0.05 if direction == "up" else -0.05

        old_value = self.current_params.importance_threshold
        new_value = max(0.1, min(0.9, old_value + adjustment))

        if new_value != old_value:
            self.current_params.importance_threshold = new_value
            changes.append(
                f"importance_threshold: {old_value:.2f} -> {new_value:.2f} "
                f"({'more' if direction == 'up' else 'less'} selective)"
            )

        return changes

    def _adjust_link_threshold(self, direction: str) -> list[str]:
        """Adjust link similarity threshold.

        Args:
            direction: "up" for fewer, stronger links or "down" for more, weaker links

        Returns:
            List of changes made
        """
        changes: list[str] = []
        adjustment = 0.05 if direction == "up" else -0.05

        old_value = self.current_params.link_similarity_threshold
        new_value = max(0.5, min(0.95, old_value + adjustment))

        if new_value != old_value:
            self.current_params.link_similarity_threshold = new_value
            changes.append(
                f"link_similarity_threshold: {old_value:.2f} -> {new_value:.2f} "
                f"({'stricter' if direction == 'up' else 'looser'} linking)"
            )

        return changes

    def _adjust_retrieval_params(self) -> list[str]:
        """Adjust retrieval parameters.

        Returns:
            List of changes made
        """
        changes: list[str] = []

        # Increase retrieval count
        old_k = self.current_params.retrieval_top_k
        new_k = min(50, old_k + 5)

        if new_k != old_k:
            self.current_params.retrieval_top_k = new_k
            changes.append(f"retrieval_top_k: {old_k} -> {new_k} (retrieve more results)")

        return changes

    async def _get_llm_suggestions(
        self,
        issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Use Claude to suggest parameter changes based on issues.

        Args:
            issues: List of detected issues

        Returns:
            List of suggestions for parameter adjustments
        """
        prompt = f"""Analyze these memory system issues and suggest parameter adjustments.

Current parameters:
- decay_rate_facts: {self.current_params.decay_rate_facts}
- decay_rate_beliefs: {self.current_params.decay_rate_beliefs}
- decay_rate_experiences: {self.current_params.decay_rate_experiences}
- importance_threshold: {self.current_params.importance_threshold}
- link_similarity_threshold: {self.current_params.link_similarity_threshold}
- retrieval_top_k: {self.current_params.retrieval_top_k}

Issues detected:
{json.dumps(issues, indent=2)}

Provide suggestions as JSON array. Each suggestion should have:
- param: parameter name
- new_value: suggested new value
- reason: brief explanation

Example:
[
  {{"param": "decay_rate_facts", "new_value": 0.93, "reason": "Reduce retention slightly to prevent overload"}},
  {{"param": "retrieval_top_k", "new_value": 15, "reason": "Increase retrieval count for better recall"}}
]

Only suggest adjustments that make sense for the specific issues. Keep values in valid ranges:
- decay_rates: 0.5 to 0.99
- importance_threshold: 0.1 to 0.9
- link_similarity_threshold: 0.5 to 0.95
- retrieval_top_k: 5 to 50"""

        try:
            response = await claude_client.complete(
                prompt=prompt,
                system=(
                    "You are a memory system optimization expert. "
                    "Analyze issues and suggest precise parameter adjustments. "
                    "Always respond with valid JSON array."
                ),
                max_tokens=2048,
            )

            # Extract JSON from response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            suggestions = json.loads(response)

            if not isinstance(suggestions, list):
                logger.warning("LLM returned non-list suggestions")
                return []

            logger.info(f"LLM suggested {len(suggestions)} parameter adjustments")
            return suggestions

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM suggestions as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting LLM suggestions: {e}")
            return []

    def _apply_suggestion(self, suggestion: dict[str, Any]) -> str | None:
        """Apply a single LLM suggestion.

        Args:
            suggestion: Suggestion dict with param, new_value, reason

        Returns:
            Description of change made, or None if invalid
        """
        param = suggestion.get("param", "")
        new_value = suggestion.get("new_value")
        reason = suggestion.get("reason", "")

        if not param or new_value is None:
            return None

        # Validate parameter exists
        if not hasattr(self.current_params, param):
            logger.warning(f"Invalid parameter in suggestion: {param}")
            return None

        old_value = getattr(self.current_params, param)

        # Validate new value type matches
        if type(new_value) != type(old_value):  # noqa: E721
            logger.warning(
                f"Type mismatch for {param}: {type(new_value)} vs {type(old_value)}"
            )
            return None

        # Validate ranges
        if param in ["decay_rate_facts", "decay_rate_beliefs", "decay_rate_experiences"]:
            if not (0.5 <= new_value <= 0.99):
                logger.warning(f"Invalid decay rate: {new_value}")
                return None
        elif param == "importance_threshold":
            if not (0.1 <= new_value <= 0.9):
                logger.warning(f"Invalid importance threshold: {new_value}")
                return None
        elif param == "link_similarity_threshold":
            if not (0.5 <= new_value <= 0.95):
                logger.warning(f"Invalid link threshold: {new_value}")
                return None
        elif param == "retrieval_top_k":
            if not (5 <= new_value <= 50):
                logger.warning(f"Invalid retrieval_top_k: {new_value}")
                return None

        # Apply change
        setattr(self.current_params, param, new_value)

        if isinstance(old_value, float):
            change_desc = f"{param}: {old_value:.2f} -> {new_value:.2f} ({reason})"
        else:
            change_desc = f"{param}: {old_value} -> {new_value} ({reason})"

        logger.info(f"Applied LLM suggestion: {change_desc}")
        return change_desc

    async def rollback(self) -> dict[str, Any]:
        """Rollback to previous parameter version.

        Returns:
            Rollback summary with restored parameters
        """
        if not self.history_file.exists():
            return {
                "success": False,
                "message": "No history available for rollback",
            }

        try:
            with open(self.history_file) as f:
                history = json.load(f)

            if len(history) < 2:
                return {
                    "success": False,
                    "message": "No previous version available",
                }

            # Remove current version and restore previous
            history.pop()
            previous_params = history[-1]

            # Restore parameters
            old_params = self.current_params.to_dict()
            self.current_params = MemoryParams(**previous_params)

            # Save restored params
            self._save_params()

            # Update history
            with open(self.history_file, "w") as f:
                json.dump(history, f, indent=2)

            logger.info("Rolled back to previous parameters")

            return {
                "success": True,
                "message": "Rolled back to previous version",
                "old_params": old_params,
                "restored_params": self.current_params.to_dict(),
            }

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {
                "success": False,
                "message": f"Rollback failed: {e}",
            }

    def get_current_params(self) -> dict[str, Any]:
        """Get current parameter state.

        Returns:
            Dictionary of current parameters
        """
        return self.current_params.to_dict()

    async def get_param_history(self) -> list[dict[str, Any]]:
        """Get parameter change history.

        Returns:
            List of historical parameter states
        """
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return []

    async def reset_to_defaults(self) -> dict[str, Any]:
        """Reset parameters to defaults.

        Returns:
            Reset summary
        """
        old_params = self.current_params.to_dict()

        # Save current to history
        self._save_param_history()

        # Reset to defaults
        params_dict = self.DEFAULT_PARAMS.copy()
        params_dict["updated_at"] = datetime.now(UTC).isoformat()
        self.current_params = MemoryParams(**params_dict)  # type: ignore

        # Save
        self._save_params()

        logger.info("Reset parameters to defaults")

        return {
            "success": True,
            "message": "Parameters reset to defaults",
            "old_params": old_params,
            "new_params": self.current_params.to_dict(),
        }
