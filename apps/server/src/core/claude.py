"""Claude API client via proxy."""

import json
import logging
from typing import Any

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for Claude API through ccproxy."""

    def __init__(self) -> None:
        # Use internal proxy URL on Railway
        self.base_url = settings.claude_proxy_url
        logger.info(f"Claude client using proxy: {self.base_url}")

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
        model: str | None = None,
    ) -> str:
        """Generate a completion from Claude via proxy."""
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers={"Content-Type": "application/json"},
                json={
                    "model": model or settings.claude_model,
                    "max_tokens": max_tokens,
                    "system": system or (
                        "You are Observer, a helpful AI assistant that analyzes "
                        "user behavior patterns and suggests automations."
                    ),
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return str(data["content"][0]["text"])

    async def analyze_patterns(
        self,
        patterns_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze patterns and generate insights."""
        prompt = f"""Analyze these user behavior patterns:
{patterns_data}

Provide JSON with: observations, automations, suggestions"""

        result = await self.complete(
            prompt=prompt,
            system=(
                "You are an AI analyst specialized in user behavior patterns. "
                "Always respond with valid JSON."
            ),
        )

        try:
            return dict(json.loads(result))
        except json.JSONDecodeError:
            return {"observations": [], "automations": [], "suggestions": []}

    async def generate_agent_code(
        self,
        agent_type: str,
        trigger_config: dict[str, Any],
        actions: list[dict[str, Any]],
    ) -> str:
        """Generate code for an agent."""
        prompt = f"""Generate Python async function for agent:
- Type: {agent_type}
- Trigger: {trigger_config}
- Actions: {actions}

Only output Python code."""

        return await self.complete(
            prompt=prompt,
            system=(
                "You are an expert Python developer. "
                "Generate clean, production-ready async code."
            ),
        )


# Global client instance
claude_client = ClaudeClient()
