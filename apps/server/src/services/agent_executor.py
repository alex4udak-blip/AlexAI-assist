"""Agent execution service."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

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
        """Make an HTTP request with SSRF protection."""
        url = self._render_template(action.get("url", ""), context)
        method = action.get("method", "GET").upper()
        headers = action.get("headers", {})
        body = action.get("body")

        # SSRF Protection: validate URL
        try:
            parsed = urlparse(url)

            # Only allow http/https
            if parsed.scheme not in ("http", "https"):
                return {
                    "success": False,
                    "error": f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.",
                    "type": "http",
                }

            # Block internal/private networks
            blocked_hosts = [
                "localhost", "127.0.0.1", "0.0.0.0",
                "169.254.169.254",  # AWS metadata
                "metadata.google.internal",  # GCP metadata
            ]
            blocked_patterns = [
                ".internal", ".local", ".railway.internal",
                "10.", "172.16.", "172.17.", "172.18.", "172.19.",
                "172.20.", "172.21.", "172.22.", "172.23.",
                "172.24.", "172.25.", "172.26.", "172.27.",
                "172.28.", "172.29.", "172.30.", "172.31.",
                "192.168.",
            ]

            hostname = parsed.hostname or ""
            if hostname in blocked_hosts:
                return {
                    "success": False,
                    "error": "URL points to blocked host",
                    "type": "http",
                }

            for pattern in blocked_patterns:
                if hostname.startswith(pattern) or hostname.endswith(pattern):
                    return {
                        "success": False,
                        "error": "URL points to internal/private network",
                        "type": "http",
                    }

        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid URL: {e}",
                "type": "http",
            }

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
        """Evaluate a condition safely."""
        condition = action.get("condition", "")

        # Safe condition evaluation using simple comparison parsing
        try:
            result = self._safe_eval_condition(condition, context)
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

    def _safe_eval_condition(
        self,
        condition: str,
        context: dict[str, Any],
    ) -> bool:
        """Safely evaluate simple conditions without eval().

        Supports: ==, !=, >, <, >=, <=, 'in', 'not in', 'and', 'or'
        """
        import operator

        condition = condition.strip()

        # Handle 'and' / 'or' by splitting and recursing
        if " and " in condition:
            parts = condition.split(" and ", 1)
            return self._safe_eval_condition(parts[0], context) and \
                   self._safe_eval_condition(parts[1], context)

        if " or " in condition:
            parts = condition.split(" or ", 1)
            return self._safe_eval_condition(parts[0], context) or \
                   self._safe_eval_condition(parts[1], context)

        # Parse comparison operators
        operators_map = {
            "==": operator.eq,
            "!=": operator.ne,
            ">=": operator.ge,
            "<=": operator.le,
            ">": operator.gt,
            "<": operator.lt,
            " in ": lambda a, b: a in b,
            " not in ": lambda a, b: a not in b,
        }

        for op_str, op_func in operators_map.items():
            if op_str in condition:
                parts = condition.split(op_str, 1)
                if len(parts) == 2:
                    left = self._resolve_value(parts[0].strip(), context)
                    right = self._resolve_value(parts[1].strip(), context)
                    return op_func(left, right)

        # If no operator, treat as boolean context lookup
        return bool(self._resolve_value(condition, context))

    def _resolve_value(self, value: str, context: dict[str, Any]) -> Any:
        """Resolve a value from context or parse as literal."""
        value = value.strip()

        # Check if it's a context variable
        if value in context:
            return context[value]

        # Try to parse as JSON literal (handles strings, numbers, booleans, null)
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

        # Try as quoted string
        if (value.startswith("'") and value.endswith("'")) or \
           (value.startswith('"') and value.endswith('"')):
            return value[1:-1]

        # Return as-is (string)
        return value

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
