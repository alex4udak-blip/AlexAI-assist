"""Claude API client - direct Anthropic API."""

import json
import logging
from typing import Any

import httpx
from httpx import HTTPStatusError, TimeoutException

from src.core.config import settings
from src.core.retry import retry_with_backoff, with_circuit_breaker

logger = logging.getLogger(__name__)


class ClaudeClientError(Exception):
    """Custom exception for Claude client errors."""

    pass


class ClaudeClient:
    """Client for direct Anthropic API."""

    def __init__(self) -> None:
        self.base_url = "https://api.anthropic.com"
        self.api_key = settings.anthropic_api_key
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set - Claude API calls will fail")
        else:
            logger.info("Claude client initialized with direct API access")

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Anthropic API."""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    @retry_with_backoff(max_attempts=3, min_wait=1, max_wait=10)
    @with_circuit_breaker(service_name="claude_api")
    async def complete(
        self,
        prompt: str | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        model: str | None = None,
        messages: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a completion from Claude API."""
        if not self.api_key:
            raise ClaudeClientError("ANTHROPIC_API_KEY not configured")

        # Build messages array
        if messages is not None:
            msg_array = messages
        elif prompt is not None:
            msg_array = [{"role": "user", "content": prompt}]
        else:
            raise ClaudeClientError("Either 'prompt' or 'messages' must be provided")

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/v1/messages",
                    headers=self._get_headers(),
                    json={
                        "model": model or settings.claude_model,
                        "max_tokens": max_tokens,
                        "system": system or (
                            "You are Observer, a helpful AI assistant that analyzes "
                            "user behavior patterns and suggests automations."
                        ),
                        "messages": msg_array,
                    },
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()

                # Validate response structure
                if "content" not in data:
                    logger.error(f"Invalid response structure: {data}")
                    raise ClaudeClientError("Invalid response: missing 'content' field")

                if not data["content"] or not isinstance(data["content"], list):
                    raise ClaudeClientError("Invalid response: 'content' is empty or not a list")

                first_content = data["content"][0]
                if "text" not in first_content:
                    raise ClaudeClientError("Invalid response: missing 'text' in content")

                return str(first_content["text"])

        except TimeoutException as e:
            logger.error(f"Claude API timeout: {e}")
            raise ClaudeClientError("Request to Claude timed out") from e
        except HTTPStatusError as e:
            logger.error(f"Claude API HTTP error: {e.response.status_code} - {e.response.text}")
            raise ClaudeClientError(f"Claude API error: {e.response.status_code}") from e
        except Exception as e:
            if isinstance(e, ClaudeClientError):
                raise
            logger.error(f"Unexpected error calling Claude: {e}")
            raise ClaudeClientError(f"Unexpected error: {e}") from e

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
