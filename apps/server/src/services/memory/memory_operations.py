"""
Memory Operations - Memory-R1 style learned operations.
Decides ADD/UPDATE/DELETE/NOOP for each interaction.
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.memory import MemoryOperation

logger = logging.getLogger(__name__)


class MemoryOperator:
    """
    Implements Memory-R1's learned memory management.
    Decides what operations to perform on each interaction.
    """

    DECISION_PROMPT = """You are a memory manager for an AI assistant. Analyze this interaction and decide what to remember.

## CURRENT KNOWLEDGE
{current_context}

## NEW INTERACTION
User: {user_message}
Assistant: {assistant_response}

## INSTRUCTIONS
Decide what memory operations to perform. Available operations:
- ADD: Store new fact/belief about the user
- UPDATE: Modify existing memory (reinforce or correct)
- DELETE: Invalidate outdated information
- NOOP: Nothing worth remembering

For each operation, specify:
- operation: ADD/UPDATE/DELETE/NOOP
- memory_type: fact/belief/experience
- content: what to store (for ADD)
- fact_type: preference/habit/goal/demographic/skill/opinion (for ADD facts)
- memory_id: which memory to modify (for UPDATE/DELETE)
- reason: why this operation
- confidence: 0-1

Return JSON array of operations. Be selective - only important information.
Return [] if nothing to remember.

Example output:
[
  {{"operation": "ADD", "memory_type": "fact", "fact_type": "preference", "content": "User prefers dark mode", "confidence": 0.9, "reason": "User explicitly mentioned preference"}},
  {{"operation": "UPDATE", "memory_type": "belief", "memory_id": "xxx", "reinforce": true, "reason": "Confirmed user prefers concise answers"}}
]
"""

    def __init__(self, db: AsyncSession, session_id: str = "default"):
        self.db = db
        self.session_id = session_id

    async def decide_operations(
        self,
        user_message: str,
        assistant_response: str,
        current_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Decide what memory operations to perform.
        Returns list of operations to execute.
        """
        from src.core.claude import claude_client

        # Format current context
        context_str = self._format_context(current_context) if current_context else "No prior context."

        prompt = self.DECISION_PROMPT.format(
            current_context=context_str,
            user_message=user_message[:1000],
            assistant_response=assistant_response[:1000],
        )

        try:
            response = await claude_client.complete(
                prompt=prompt,
                system="You are a memory manager. Return valid JSON array only. Be selective - only remember important facts.",
            )

            # Parse response - handle potential markdown wrapping
            response = response.strip()
            if response.startswith("```"):
                # Remove markdown code blocks
                lines = response.split("\n")
                response = "\n".join(
                    line for line in lines
                    if not line.startswith("```")
                )

            operations = json.loads(response)

            # Validate and filter
            valid_ops = []
            for op in operations:
                if self._validate_operation(op):
                    valid_ops.append(op)

            logger.info(f"Memory operator decided {len(valid_ops)} operations")
            return valid_ops

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse memory operations response: {e}")
            return []
        except Exception as e:
            logger.error(f"Memory operation decision error: {e}")
            return []

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format context for prompt."""
        parts = []

        if context.get("relevant_facts"):
            facts = [f["content"] for f in context["relevant_facts"][:5]]
            parts.append(f"Known facts:\n" + "\n".join(f"- {f}" for f in facts))

        if context.get("beliefs"):
            beliefs = [b["belief"] for b in context["beliefs"][:3]]
            parts.append(f"Current beliefs:\n" + "\n".join(f"- {b}" for b in beliefs))

        if context.get("persona"):
            p = context["persona"]
            if p.get("summary"):
                parts.append(f"User profile: {p['summary'][:200]}")

        return "\n\n".join(parts) if parts else "No prior context."

    def _validate_operation(self, op: dict[str, Any]) -> bool:
        """Validate operation structure."""
        if not isinstance(op, dict):
            return False

        operation = op.get("operation")
        if operation not in ["ADD", "UPDATE", "DELETE", "NOOP"]:
            return False

        if operation == "ADD":
            if not op.get("content"):
                return False
            # Validate content is meaningful
            content = op.get("content", "")
            if len(content) < 5:
                return False

        if operation in ["UPDATE", "DELETE"]:
            if not op.get("memory_id") and not op.get("content"):
                return False

        return True

    async def log_operation(
        self,
        operation: dict[str, Any],
        success: bool = True,
        error: str | None = None,
    ) -> MemoryOperation:
        """Log memory operation for analysis."""
        memory_id = operation.get("memory_id")
        if memory_id and isinstance(memory_id, str):
            try:
                memory_id = UUID(memory_id)
            except ValueError:
                memory_id = None

        log = MemoryOperation(
            id=uuid4(),
            session_id=self.session_id,
            operation=operation.get("operation"),
            memory_type=operation.get("memory_type"),
            memory_id=memory_id,
            trigger="chat_message",
            reason=operation.get("reason"),
            confidence=operation.get("confidence"),
            success=success,
            error=error,
            created_at=datetime.utcnow(),
        )
        self.db.add(log)
        return log

    async def get_operation_stats(
        self,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Get statistics about recent operations."""
        from sqlalchemy import func, select
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=hours)

        result = await self.db.execute(
            select(
                MemoryOperation.operation,
                func.count(MemoryOperation.id),
            )
            .where(
                MemoryOperation.session_id == self.session_id,
                MemoryOperation.created_at >= cutoff,
            )
            .group_by(MemoryOperation.operation)
        )

        counts = {row[0]: row[1] for row in result.fetchall()}

        return {
            "period_hours": hours,
            "total_operations": sum(counts.values()),
            "by_type": counts,
            "add_rate": counts.get("ADD", 0) / max(1, hours),
            "update_rate": counts.get("UPDATE", 0) / max(1, hours),
        }

    async def get_recent_operations(
        self,
        limit: int = 20,
        operation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get recent operations."""
        from sqlalchemy import select

        filters = [MemoryOperation.session_id == self.session_id]
        if operation_type:
            filters.append(MemoryOperation.operation == operation_type)

        result = await self.db.execute(
            select(MemoryOperation)
            .where(*filters)
            .order_by(MemoryOperation.created_at.desc())
            .limit(limit)
        )

        operations = []
        for op in result.scalars().all():
            operations.append({
                "id": str(op.id),
                "operation": op.operation,
                "memory_type": op.memory_type,
                "memory_id": str(op.memory_id) if op.memory_id else None,
                "reason": op.reason,
                "confidence": op.confidence,
                "success": op.success,
                "error": op.error,
                "created_at": op.created_at.isoformat() if op.created_at else None,
            })

        return operations
