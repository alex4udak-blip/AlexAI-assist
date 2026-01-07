"""
Memory Operations - Memory-R1 style learned operations.
Decides ADD/UPDATE/DELETE/NOOP for each interaction.
"""

import json
import logging
import re
import unicodedata
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import validate_session_id
from src.db.models.memory import MemoryOperation

logger = logging.getLogger(__name__)


def sanitize_user_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input to prevent prompt injection attacks.

    Args:
        text: Raw user input
        max_length: Maximum allowed length

    Returns:
        Sanitized text safe for embedding in prompts
    """
    if not text or not isinstance(text, str):
        return ""

    # Step 1: Limit length
    text = text[:max_length]

    # Step 2: Strip control characters (except common whitespace)
    # Keep: \n (newline), \t (tab), \r (carriage return)
    # Remove: other control characters that could affect prompt parsing
    text = "".join(
        char for char in text
        if unicodedata.category(char)[0] != "C" or char in {"\n", "\t", "\r", " "}
    )

    # Step 3: Remove potential prompt injection patterns
    # These patterns could be used to escape the user content section
    injection_patterns = [
        r"(?i)<\|im_start\|>",  # ChatML tokens
        r"(?i)<\|im_end\|>",
        r"(?i)<\|system\|>",
        r"(?i)<\|assistant\|>",
        r"(?i)<\|user\|>",
        r"(?i)##\s*INSTRUCTIONS",  # Attempts to inject new instructions
        r"(?i)##\s*SYSTEM",
        r"(?i)##\s*OVERRIDE",
        r"(?i)IGNORE\s+PREVIOUS\s+INSTRUCTIONS",
        r"(?i)IGNORE\s+ALL\s+PREVIOUS",
        r"(?i)NEW\s+INSTRUCTIONS:",
        r"(?i)SYSTEM\s+PROMPT:",
        r"(?i)You\s+are\s+now",  # Attempts to redefine assistant role
        r"(?i)Disregard\s+all",
    ]

    for pattern in injection_patterns:
        text = re.sub(pattern, "[FILTERED]", text)

    # Step 4: Escape markdown formatting that could affect prompt structure
    # Replace triple backticks which could close/open code blocks
    text = text.replace("```", "'''")

    # Step 5: Normalize excessive whitespace
    # Prevent prompt stuffing with whitespace
    text = re.sub(r"\n{4,}", "\n\n\n", text)  # Max 3 consecutive newlines
    text = re.sub(r" {10,}", " " * 9, text)  # Max 9 consecutive spaces

    # Step 6: Remove null bytes and other problematic characters
    text = text.replace("\x00", "")
    text = text.replace("\uffff", "")

    return text.strip()


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
        # Validate session_id to prevent session forgery
        self.session_id = validate_session_id(session_id)

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

        # Sanitize user inputs to prevent prompt injection
        sanitized_user_msg = sanitize_user_input(user_message, max_length=1000)
        sanitized_assistant_resp = sanitize_user_input(assistant_response, max_length=1000)

        # Format current context
        context_str = self._format_context(current_context) if current_context else "No prior context."

        prompt = self.DECISION_PROMPT.format(
            current_context=context_str,
            user_message=sanitized_user_msg,
            assistant_response=sanitized_assistant_resp,
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
        """Format context for prompt with sanitization."""
        parts = []

        if context.get("relevant_facts"):
            # Sanitize fact content before embedding in prompt
            facts = [
                sanitize_user_input(f.get("content", ""), max_length=500)
                for f in context["relevant_facts"][:5]
            ]
            facts = [f for f in facts if f]  # Remove empty facts
            if facts:
                parts.append(f"Known facts:\n" + "\n".join(f"- {f}" for f in facts))

        if context.get("beliefs"):
            # Sanitize belief content before embedding in prompt
            beliefs = [
                sanitize_user_input(b.get("belief", ""), max_length=500)
                for b in context["beliefs"][:3]
            ]
            beliefs = [b for b in beliefs if b]  # Remove empty beliefs
            if beliefs:
                parts.append(f"Current beliefs:\n" + "\n".join(f"- {b}" for b in beliefs))

        if context.get("persona"):
            p = context["persona"]
            if p.get("summary"):
                # Sanitize persona summary before embedding in prompt
                sanitized_summary = sanitize_user_input(p["summary"], max_length=200)
                if sanitized_summary:
                    parts.append(f"User profile: {sanitized_summary}")

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
