"""Claude API client."""

from typing import Any

import httpx

from src.core.config import settings


class ClaudeClient:
    """Client for interacting with Claude API."""

    def __init__(self) -> None:
        self.base_url = "https://api.anthropic.com/v1"
        self.token = settings.claude_oauth_token

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
        model: str | None = None,
    ) -> str:
        """Generate a completion from Claude."""
        if not self.token:
            raise ValueError("Claude OAuth token not configured")

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model or settings.claude_model,
                    "max_tokens": max_tokens,
                    "system": system or "You are Observer, a helpful AI assistant that analyzes user behavior patterns and suggests automations.",
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
        prompt = f"""Analyze these user behavior patterns and provide insights:

{patterns_data}

Provide:
1. Key observations about user behavior
2. Potential automation opportunities
3. Productivity improvement suggestions

Respond in JSON format with keys: observations, automations, suggestions"""

        result = await self.complete(
            prompt=prompt,
            system="You are an AI analyst specialized in user behavior patterns. Always respond with valid JSON.",
        )

        import json
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
        prompt = f"""Generate Python code for an automation agent with:
- Type: {agent_type}
- Trigger: {trigger_config}
- Actions: {actions}

The code should:
1. Be a complete, runnable async function
2. Handle errors gracefully
3. Log actions appropriately
4. Return a status dict with success/error info

Only output the Python code, no explanations."""

        return await self.complete(
            prompt=prompt,
            system="You are an expert Python developer. Generate clean, production-ready async code.",
        )


# Global client instance
claude_client = ClaudeClient()
