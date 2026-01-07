"""Agent execution service."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from src.core.claude import claude_client
from src.db.models import Agent


class AgentExecutorService:
    """Service for executing automation agents."""

    async def execute(
        self,
        agent: Agent,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an agent's actions."""
        context = context or {}
        results: list[dict[str, Any]] = []
        success = True
        error = None

        try:
            for i, action in enumerate(agent.actions):
                action_type = action.get("type")
                action_result = await self._execute_action(
                    agent=agent,
                    action=action,
                    context=context,
                )
                results.append({
                    "action_index": i,
                    "action_type": action_type,
                    "result": action_result,
                })

                if not action_result.get("success"):
                    success = False
                    error = action_result.get("error")
                    break

                # Update context with action result
                context[f"action_{i}_result"] = action_result

        except Exception as e:
            success = False
            error = str(e)

        return {
            "success": success,
            "error": error,
            "results": results,
            "executed_at": datetime.now(UTC).isoformat(),
        }

    async def _execute_action(
        self,
        agent: Agent,
        action: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a single action."""
        action_type = action.get("type")

        handlers = {
            "notify": self._action_notify,
            "analyze": self._action_analyze,
            "http": self._action_http,
            "delay": self._action_delay,
            "condition": self._action_condition,
            "log": self._action_log,
        }

        handler = handlers.get(action_type)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown action type: {action_type}",
            }

        try:
            return await handler(action, context)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def _action_notify(
        self,
        action: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a notification."""
        template = action.get("template", "")
        message = self._render_template(template, context)

        # In production, this would send to notification service
        return {
            "success": True,
            "message": message,
            "type": "notification",
        }

    async def _action_analyze(
        self,
        action: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze data using Claude."""
        prompt = action.get("prompt", "")
        rendered_prompt = self._render_template(prompt, context)

        try:
            analysis = await claude_client.complete(rendered_prompt)
            return {
                "success": True,
                "analysis": analysis,
                "type": "analysis",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Analysis failed: {e}",
            }

    async def _action_http(
        self,
        action: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Make an HTTP request."""
        import httpx

        url = self._render_template(action.get("url", ""), context)
        method = action.get("method", "GET").upper()
        headers = action.get("headers", {})
        body = action.get("body")

        if body:
            body = self._render_template(json.dumps(body), context)
            body = json.loads(body)

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if method in ("POST", "PUT", "PATCH") else None,
            )

            return {
                "success": response.is_success,
                "status_code": response.status_code,
                "body": response.text[:1000],
                "type": "http",
            }

    async def _action_delay(
        self,
        action: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Wait for a specified duration."""
        seconds = action.get("seconds", 1)
        await asyncio.sleep(min(seconds, 60))  # Max 60 seconds
        return {
            "success": True,
            "waited_seconds": seconds,
            "type": "delay",
        }

    async def _action_condition(
        self,
        action: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a condition."""
        condition = action.get("condition", "")
        # Simple condition evaluation (in production, use safer eval)
        try:
            result = eval(condition, {"__builtins__": {}}, context)
            return {
                "success": True,
                "result": bool(result),
                "type": "condition",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Condition evaluation failed: {e}",
            }

    async def _action_log(
        self,
        action: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Log a message."""
        message = action.get("message", "")
        rendered = self._render_template(message, context)
        return {
            "success": True,
            "logged": rendered,
            "type": "log",
        }

    def _render_template(
        self,
        template: str,
        context: dict[str, Any],
    ) -> str:
        """Render a template string with context variables."""
        result = template
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result


# Global executor instance
agent_executor = AgentExecutorService()
