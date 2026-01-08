"""Code proposals service for structural improvements."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from src.core.claude import claude_client
from src.core.logging import get_logger, log_error

logger = get_logger(__name__)


class CodeProposalService:
    """Service for generating and managing code change proposals."""

    def __init__(self) -> None:
        self._proposals: dict[str, dict[str, Any]] = {}

    async def generate(
        self,
        issues: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """
        Analyze issues and generate code proposals.

        Args:
            issues: Dictionary with keys: 'feature_requests', 'bugs', 'improvements'

        Returns:
            List of generated proposals
        """
        proposals: list[dict[str, Any]] = []

        logger.info(
            "Generating code proposals",
            extra={
                "event_type": "proposal_generation_started",
                "feature_requests": len(issues.get("feature_requests", [])),
                "bugs": len(issues.get("bugs", [])),
                "improvements": len(issues.get("improvements", [])),
            },
        )

        try:
            if issues.get("feature_requests"):
                feature_proposal = await self._generate_feature_proposal(
                    issues["feature_requests"]
                )
                if feature_proposal:
                    self._proposals[feature_proposal["id"]] = feature_proposal
                    proposals.append(feature_proposal)

            if issues.get("bugs"):
                bugfix_proposal = await self._generate_bugfix_proposal(
                    issues["bugs"]
                )
                if bugfix_proposal:
                    self._proposals[bugfix_proposal["id"]] = bugfix_proposal
                    proposals.append(bugfix_proposal)

            if issues.get("improvements"):
                improvement_proposal = await self._generate_improvement_proposal(
                    issues["improvements"]
                )
                if improvement_proposal:
                    self._proposals[improvement_proposal["id"]] = improvement_proposal
                    proposals.append(improvement_proposal)

            logger.info(
                f"Generated {len(proposals)} code proposals",
                extra={
                    "event_type": "proposal_generation_completed",
                    "proposal_count": len(proposals),
                },
            )

        except Exception as e:
            log_error(
                logger,
                "Failed to generate code proposals",
                error=e,
                extra={"event_type": "proposal_generation_error"},
            )

        return proposals

    async def _generate_feature_proposal(
        self,
        requests: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Generate feature addition proposal.

        Args:
            requests: List of feature requests to analyze

        Returns:
            Feature proposal or None if generation fails
        """
        logger.debug(
            f"Generating feature proposal from {len(requests)} requests",
            extra={"event_type": "feature_proposal_generation"},
        )

        try:
            prompt = f"""Analyze these feature requests and create a comprehensive feature addition proposal:

Feature Requests:
{json.dumps(requests, indent=2)}

Generate a JSON response with:
- title: Brief feature title
- description: Detailed description of the feature and its benefits
- affected_files: Array of file paths that need changes
- implementation_steps: Array of step-by-step implementation instructions
- code_snippets: Object with filename keys and code snippet values showing key implementations
- estimated_effort: String (low/medium/high)
- priority: String (low/medium/high)

Respond ONLY with valid JSON."""

            response = await claude_client.complete(
                prompt=prompt,
                system=(
                    "You are a senior software architect. Analyze feature requests and "
                    "create detailed, actionable implementation proposals. Focus on clean "
                    "architecture, maintainability, and user value. Always respond with valid JSON."
                ),
                max_tokens=4096,
            )

            proposal_data = json.loads(response)

            proposal = {
                "id": str(uuid.uuid4()),
                "type": "feature",
                "title": proposal_data.get("title", "New Feature"),
                "description": proposal_data.get("description", ""),
                "affected_files": proposal_data.get("affected_files", []),
                "implementation_steps": proposal_data.get("implementation_steps", []),
                "code_snippets": proposal_data.get("code_snippets", {}),
                "estimated_effort": proposal_data.get("estimated_effort", "medium"),
                "priority": proposal_data.get("priority", "medium"),
                "status": "pending_review",
                "created_at": datetime.now(UTC).isoformat(),
                "source_requests": requests,
            }

            logger.info(
                f"Generated feature proposal: {proposal['title']}",
                extra={
                    "event_type": "feature_proposal_created",
                    "proposal_id": proposal["id"],
                    "affected_files": len(proposal["affected_files"]),
                },
            )

            return proposal

        except json.JSONDecodeError as e:
            log_error(
                logger,
                "Failed to parse feature proposal JSON",
                error=e,
                extra={"event_type": "feature_proposal_json_error"},
            )
            return None
        except Exception as e:
            log_error(
                logger,
                "Failed to generate feature proposal",
                error=e,
                extra={"event_type": "feature_proposal_error"},
            )
            return None

    async def _generate_bugfix_proposal(
        self,
        bugs: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Generate bugfix proposal.

        Args:
            bugs: List of bugs to analyze

        Returns:
            Bugfix proposal or None if generation fails
        """
        logger.debug(
            f"Generating bugfix proposal from {len(bugs)} bugs",
            extra={"event_type": "bugfix_proposal_generation"},
        )

        try:
            prompt = f"""Analyze these bugs and create a comprehensive bugfix proposal:

Bugs:
{json.dumps(bugs, indent=2)}

Generate a JSON response with:
- title: Brief fix title
- description: Detailed description of the bugs and root causes
- affected_files: Array of file paths that need changes
- implementation_steps: Array of step-by-step fix instructions
- code_changes: Array of objects with 'file', 'location', 'current_code', 'fixed_code', 'explanation'
- test_requirements: Array of testing requirements
- severity: String (low/medium/high/critical)
- estimated_effort: String (low/medium/high)

Respond ONLY with valid JSON."""

            response = await claude_client.complete(
                prompt=prompt,
                system=(
                    "You are a senior debugging expert. Analyze bugs, identify root causes, "
                    "and create detailed fix proposals with clear explanations. Focus on "
                    "correctness, edge cases, and preventing regressions. Always respond with valid JSON."
                ),
                max_tokens=4096,
            )

            proposal_data = json.loads(response)

            proposal = {
                "id": str(uuid.uuid4()),
                "type": "bugfix",
                "title": proposal_data.get("title", "Bug Fix"),
                "description": proposal_data.get("description", ""),
                "affected_files": proposal_data.get("affected_files", []),
                "implementation_steps": proposal_data.get("implementation_steps", []),
                "code_changes": proposal_data.get("code_changes", []),
                "test_requirements": proposal_data.get("test_requirements", []),
                "severity": proposal_data.get("severity", "medium"),
                "estimated_effort": proposal_data.get("estimated_effort", "medium"),
                "status": "pending_review",
                "created_at": datetime.now(UTC).isoformat(),
                "source_bugs": bugs,
            }

            logger.info(
                f"Generated bugfix proposal: {proposal['title']}",
                extra={
                    "event_type": "bugfix_proposal_created",
                    "proposal_id": proposal["id"],
                    "severity": proposal["severity"],
                },
            )

            return proposal

        except json.JSONDecodeError as e:
            log_error(
                logger,
                "Failed to parse bugfix proposal JSON",
                error=e,
                extra={"event_type": "bugfix_proposal_json_error"},
            )
            return None
        except Exception as e:
            log_error(
                logger,
                "Failed to generate bugfix proposal",
                error=e,
                extra={"event_type": "bugfix_proposal_error"},
            )
            return None

    async def _generate_improvement_proposal(
        self,
        improvements: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Generate improvement proposal for code quality/performance.

        Args:
            improvements: List of improvement opportunities to analyze

        Returns:
            Improvement proposal or None if generation fails
        """
        logger.debug(
            f"Generating improvement proposal from {len(improvements)} items",
            extra={"event_type": "improvement_proposal_generation"},
        )

        try:
            prompt = f"""Analyze these improvement opportunities and create a comprehensive refactoring proposal:

Improvements:
{json.dumps(improvements, indent=2)}

Generate a JSON response with:
- title: Brief improvement title
- description: Detailed description of improvements and their benefits
- affected_files: Array of file paths that need changes
- implementation_steps: Array of step-by-step refactoring instructions
- code_changes: Array of objects with 'file', 'location', 'current_code', 'improved_code', 'explanation'
- benefits: Array of specific benefits (performance, maintainability, etc.)
- risks: Array of potential risks or breaking changes
- estimated_effort: String (low/medium/high)
- priority: String (low/medium/high)

Respond ONLY with valid JSON."""

            response = await claude_client.complete(
                prompt=prompt,
                system=(
                    "You are a senior code quality expert. Analyze improvement opportunities "
                    "and create detailed refactoring proposals. Focus on clean code principles, "
                    "performance optimization, and maintainability. Always consider backward "
                    "compatibility and testing. Always respond with valid JSON."
                ),
                max_tokens=4096,
            )

            proposal_data = json.loads(response)

            proposal = {
                "id": str(uuid.uuid4()),
                "type": "improvement",
                "title": proposal_data.get("title", "Code Improvement"),
                "description": proposal_data.get("description", ""),
                "affected_files": proposal_data.get("affected_files", []),
                "implementation_steps": proposal_data.get("implementation_steps", []),
                "code_changes": proposal_data.get("code_changes", []),
                "benefits": proposal_data.get("benefits", []),
                "risks": proposal_data.get("risks", []),
                "estimated_effort": proposal_data.get("estimated_effort", "medium"),
                "priority": proposal_data.get("priority", "medium"),
                "status": "pending_review",
                "created_at": datetime.now(UTC).isoformat(),
                "source_improvements": improvements,
            }

            logger.info(
                f"Generated improvement proposal: {proposal['title']}",
                extra={
                    "event_type": "improvement_proposal_created",
                    "proposal_id": proposal["id"],
                    "benefits_count": len(proposal["benefits"]),
                },
            )

            return proposal

        except json.JSONDecodeError as e:
            log_error(
                logger,
                "Failed to parse improvement proposal JSON",
                error=e,
                extra={"event_type": "improvement_proposal_json_error"},
            )
            return None
        except Exception as e:
            log_error(
                logger,
                "Failed to generate improvement proposal",
                error=e,
                extra={"event_type": "improvement_proposal_error"},
            )
            return None

    async def get_pending_proposals(self) -> list[dict[str, Any]]:
        """
        Get all proposals pending review.

        Returns:
            List of pending proposals
        """
        pending = [
            proposal
            for proposal in self._proposals.values()
            if proposal["status"] == "pending_review"
        ]

        logger.debug(
            f"Retrieved {len(pending)} pending proposals",
            extra={
                "event_type": "get_pending_proposals",
                "count": len(pending),
            },
        )

        return pending

    async def approve_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        """
        Mark proposal as approved.

        Args:
            proposal_id: ID of the proposal to approve

        Returns:
            Updated proposal or None if not found
        """
        proposal = self._proposals.get(proposal_id)

        if not proposal:
            logger.warning(
                f"Proposal not found: {proposal_id}",
                extra={
                    "event_type": "proposal_not_found",
                    "proposal_id": proposal_id,
                },
            )
            return None

        proposal["status"] = "approved"
        proposal["approved_at"] = datetime.now(UTC).isoformat()

        logger.info(
            f"Approved proposal: {proposal['title']}",
            extra={
                "event_type": "proposal_approved",
                "proposal_id": proposal_id,
                "type": proposal["type"],
            },
        )

        return proposal

    async def reject_proposal(
        self,
        proposal_id: str,
        reason: str,
    ) -> dict[str, Any] | None:
        """
        Mark proposal as rejected.

        Args:
            proposal_id: ID of the proposal to reject
            reason: Reason for rejection

        Returns:
            Updated proposal or None if not found
        """
        proposal = self._proposals.get(proposal_id)

        if not proposal:
            logger.warning(
                f"Proposal not found: {proposal_id}",
                extra={
                    "event_type": "proposal_not_found",
                    "proposal_id": proposal_id,
                },
            )
            return None

        proposal["status"] = "rejected"
        proposal["rejected_at"] = datetime.now(UTC).isoformat()
        proposal["rejection_reason"] = reason

        logger.info(
            f"Rejected proposal: {proposal['title']}",
            extra={
                "event_type": "proposal_rejected",
                "proposal_id": proposal_id,
                "type": proposal["type"],
                "reason": reason,
            },
        )

        return proposal

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        """
        Get a specific proposal by ID.

        Args:
            proposal_id: ID of the proposal

        Returns:
            Proposal or None if not found
        """
        return self._proposals.get(proposal_id)

    def get_all_proposals(self) -> list[dict[str, Any]]:
        """
        Get all proposals regardless of status.

        Returns:
            List of all proposals
        """
        return list(self._proposals.values())


# Global service instance
code_proposal_service = CodeProposalService()
