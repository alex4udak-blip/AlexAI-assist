"""Agent execution service."""

import asyncio
import json
import operator
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from src.core.claude import claude_client
from src.core.logging import get_logger, log_error, log_security_event
from src.core.retry import retry_with_backoff, with_circuit_breaker
from src.core.websocket import broadcast_event
from src.db.models import Agent

logger = get_logger(__name__)


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

        logger.info(
            f"Starting agent execution: {agent.name}",
            extra={
                "event_type": "agent_execution_started",
                "agent_id": str(agent.id),
                "agent_name": agent.name,
                "action_count": len(agent.actions),
            },
        )

        try:
            for i, action in enumerate(agent.actions):
                action_type = action.get("type")
                logger.debug(
                    f"Executing action {i + 1}/{len(agent.actions)}: {action_type}",
                    extra={
                        "event_type": "agent_action_started",
                        "agent_id": str(agent.id),
                        "action_index": i,
                        "action_type": action_type,
                    },
                )

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
                    log_error(
                        logger,
                        f"Agent action failed: {action_type}",
                        extra={
                            "event_type": "agent_action_failed",
                            "agent_id": str(agent.id),
                            "action_index": i,
                            "action_type": action_type,
                            "error": error,
                        },
                    )
                    break

                # Update context with action result
                context[f"action_{i}_result"] = action_result

            logger.info(
                f"Agent execution {'completed' if success else 'failed'}: {agent.name}",
                extra={
                    "event_type": "agent_execution_completed",
                    "agent_id": str(agent.id),
                    "success": success,
                    "actions_executed": len(results),
                },
            )

        except Exception as e:
            success = False
            error = str(e)
            log_error(
                logger,
                f"Agent execution error: {agent.name}",
                error=e,
                extra={
                    "event_type": "agent_execution_error",
                    "agent_id": str(agent.id),
                },
            )

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
        action_type = action.get("type", "")

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
            log_error(
                logger,
                f"Action handler error: {action_type}",
                error=e,
                extra={
                    "event_type": "action_handler_error",
                    "action_type": action_type,
                },
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def _action_notify(
        self,
        action: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a notification via logging and WebSocket broadcast."""
        template = action.get("template", "")
        message = self._render_template(template, context)
        title = action.get("title", "Agent Notification")
        priority = action.get("priority", "normal")

        # Log the notification
        logger.info(
            f"Agent notification: {message}",
            extra={
                "event_type": "agent_notification",
                "notification_title": title,
                "notification_message": message,
                "priority": priority,
                "context_keys": list(context.keys()),
            },
        )

        # Broadcast to connected desktop clients via WebSocket
        try:
            await broadcast_event("notification", {
                "title": title,
                "message": message,
                "priority": priority,
                "timestamp": datetime.now(UTC).isoformat(),
            })
        except Exception as e:
            # Don't fail the action if broadcast fails - just log it
            logger.warning(
                "Failed to broadcast notification via WebSocket",
                extra={
                    "event_type": "notification_broadcast_failed",
                    "error": str(e),
                },
            )

        return {
            "success": True,
            "message": message,
            "title": title,
            "priority": priority,
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
            logger.debug(
                "Claude analysis completed",
                extra={
                    "event_type": "claude_analysis",
                    "prompt_length": len(rendered_prompt),
                    "response_length": len(analysis),
                },
            )
            return {
                "success": True,
                "analysis": analysis,
                "type": "analysis",
            }
        except Exception as e:
            log_error(
                logger,
                "Claude analysis failed",
                error=e,
                extra={"event_type": "claude_analysis_error"},
            )
            return {
                "success": False,
                "error": f"Analysis failed: {e}",
            }

    @retry_with_backoff(max_attempts=3, min_wait=1, max_wait=10)
    @with_circuit_breaker(service_name="agent_http")
    async def _make_http_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None,
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if method in ("POST", "PUT", "PATCH") else None,
            )
            # Raise for 5xx errors to trigger retry
            if 500 <= response.status_code < 600:
                response.raise_for_status()
            return response

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
                log_security_event(
                    logger,
                    "HTTP action blocked: invalid URL scheme",
                    details={
                        "scheme": parsed.scheme,
                        "url": url[:100],  # Truncate for logging
                    },
                )
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
                log_security_event(
                    logger,
                    "SSRF attempt blocked: blocked host",
                    details={"hostname": hostname},
                    level="ERROR",
                )
                return {
                    "success": False,
                    "error": "URL points to blocked host",
                    "type": "http",
                }

            for pattern in blocked_patterns:
                if hostname.startswith(pattern) or hostname.endswith(pattern):
                    log_security_event(
                        logger,
                        "SSRF attempt blocked: private network",
                        details={"hostname": hostname, "pattern": pattern},
                        level="ERROR",
                    )
                    return {
                        "success": False,
                        "error": "URL points to internal/private network",
                        "type": "http",
                    }

        except Exception as e:
            log_error(
                logger,
                "HTTP action URL validation failed",
                error=e,
                extra={"event_type": "http_url_validation_error"},
            )
            return {
                "success": False,
                "error": f"Invalid URL: {e}",
                "type": "http",
            }

        if body:
            body = self._render_template(json.dumps(body), context)
            body = json.loads(body)

        try:
            response = await self._make_http_request(
                method=method,
                url=url,
                headers=headers,
                body=body,
            )

            logger.info(
                f"HTTP request completed: {method} {url}",
                extra={
                    "event_type": "http_request",
                    "method": method,
                    "url": url[:100],  # Truncate for logging
                    "status_code": response.status_code,
                },
            )

            return {
                "success": response.is_success,
                "status_code": response.status_code,
                "body": response.text[:1000],
                "type": "http",
            }
        except Exception as e:
            log_error(
                logger,
                f"HTTP request failed: {method} {url}",
                error=e,
                extra={
                    "event_type": "http_request_error",
                    "method": method,
                    "url": url[:100],
                },
            )
            return {
                "success": False,
                "error": f"HTTP request failed: {e}",
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
        def contains(a: Any, b: Any) -> bool:
            return a in b

        def not_contains(a: Any, b: Any) -> bool:
            return a not in b

        operators_map: dict[str, Callable[[Any, Any], bool]] = {
            "==": operator.eq,
            "!=": operator.ne,
            ">=": operator.ge,
            "<=": operator.le,
            ">": operator.gt,
            "<": operator.lt,
            " in ": contains,
            " not in ": not_contains,
        }

        for op_str, op_func in operators_map.items():
            if op_str in condition:
                parts = condition.split(op_str, 1)
                if len(parts) == 2:
                    left = self._resolve_value(parts[0].strip(), context)
                    right = self._resolve_value(parts[1].strip(), context)
                    return bool(op_func(left, right))

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
            # Value is not valid JSON, will try other parsing methods below
            logger.debug(
                "Value is not valid JSON, treating as string",
                extra={"value": value[:50] if len(value) > 50 else value},
            )

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
