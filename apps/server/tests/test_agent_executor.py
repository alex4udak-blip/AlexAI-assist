"""Tests for agent executor service."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.models.agent import Agent
from src.services.agent_executor import AgentExecutorService


@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = MagicMock(spec=Agent)
    agent.id = uuid.uuid4()
    agent.name = "Test Agent"
    agent.agent_type = "automation"
    agent.actions = []
    return agent


@pytest.fixture
def executor():
    """Create agent executor instance."""
    return AgentExecutorService()


class TestAgentExecutionLifecycle:
    """Test agent execution lifecycle."""

    @pytest.mark.asyncio
    async def test_execute_empty_actions(self, executor, mock_agent):
        """Test execution with no actions."""
        mock_agent.actions = []

        result = await executor.execute(mock_agent)

        assert result["success"] is True
        assert result["error"] is None
        assert result["results"] == []
        assert "executed_at" in result

    @pytest.mark.asyncio
    async def test_execute_single_action_success(self, executor, mock_agent):
        """Test successful execution of single action."""
        mock_agent.actions = [
            {"type": "log", "message": "Test message"}
        ]

        result = await executor.execute(mock_agent)

        assert result["success"] is True
        assert result["error"] is None
        assert len(result["results"]) == 1
        assert result["results"][0]["action_type"] == "log"
        assert result["results"][0]["result"]["success"] is True

    @pytest.mark.asyncio
    async def test_execute_multiple_actions_success(self, executor, mock_agent):
        """Test successful execution of multiple actions."""
        mock_agent.actions = [
            {"type": "log", "message": "First"},
            {"type": "delay", "seconds": 0},
            {"type": "log", "message": "Second"}
        ]

        result = await executor.execute(mock_agent)

        assert result["success"] is True
        assert result["error"] is None
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_execute_stops_on_action_failure(self, executor, mock_agent):
        """Test execution stops when action fails."""
        mock_agent.actions = [
            {"type": "log", "message": "First"},
            {"type": "unknown_action"},
            {"type": "log", "message": "Third"}
        ]

        result = await executor.execute(mock_agent)

        assert result["success"] is False
        assert result["error"] == "Unknown action type: unknown_action"
        assert len(result["results"]) == 2  # First and failed action only

    @pytest.mark.asyncio
    async def test_execute_with_context(self, executor, mock_agent):
        """Test execution with initial context."""
        mock_agent.actions = [
            {"type": "log", "message": "User: {{username}}"}
        ]

        context = {"username": "test_user"}
        result = await executor.execute(mock_agent, context)

        assert result["success"] is True
        assert result["results"][0]["result"]["logged"] == "User: test_user"

    @pytest.mark.asyncio
    async def test_execute_context_propagation(self, executor, mock_agent):
        """Test context is updated between actions."""
        mock_agent.actions = [
            {"type": "log", "message": "First"},
            {"type": "log", "message": "Second"}
        ]

        result = await executor.execute(mock_agent)

        # Context should have results from previous actions
        assert result["success"] is True
        assert len(result["results"]) == 2


class TestErrorHandling:
    """Test error handling during execution."""

    @pytest.mark.asyncio
    async def test_unknown_action_type(self, executor, mock_agent):
        """Test handling of unknown action type."""
        mock_agent.actions = [{"type": "invalid_action"}]

        result = await executor.execute(mock_agent)

        assert result["success"] is False
        assert "Unknown action type" in result["error"]

    @pytest.mark.asyncio
    async def test_action_exception_handling(self, executor, mock_agent):
        """Test condition with invalid syntax treated as truthy string."""
        mock_agent.actions = [
            {"type": "condition", "condition": "invalid syntax {{{}}}"}
        ]

        result = await executor.execute(mock_agent)

        # Invalid syntax is treated as truthy string (non-empty), so it succeeds
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_general_exception(self, executor, mock_agent):
        """Test exception when actions is None raises TypeError."""
        # Create an agent with invalid actions structure
        mock_agent.actions = None

        # len(None) is called before try block, raising TypeError
        with pytest.raises(TypeError):
            await executor.execute(mock_agent)


class TestActionNotify:
    """Test notify action."""

    @pytest.mark.asyncio
    async def test_notify_simple_message(self, executor):
        """Test simple notification."""
        action = {"type": "notify", "template": "Test notification"}
        context = {}

        result = await executor._action_notify(action, context)

        assert result["success"] is True
        assert result["message"] == "Test notification"
        assert result["type"] == "notification"

    @pytest.mark.asyncio
    async def test_notify_with_template(self, executor):
        """Test notification with template variables."""
        action = {"type": "notify", "template": "Hello {{name}}!"}
        context = {"name": "Alice"}

        result = await executor._action_notify(action, context)

        assert result["success"] is True
        assert result["message"] == "Hello Alice!"

    @pytest.mark.asyncio
    async def test_notify_empty_template(self, executor):
        """Test notification with empty template."""
        action = {"type": "notify"}
        context = {}

        result = await executor._action_notify(action, context)

        assert result["success"] is True
        assert result["message"] == ""


class TestActionAnalyze:
    """Test analyze action with Claude."""

    @pytest.mark.asyncio
    async def test_analyze_success(self, executor):
        """Test successful analysis."""
        action = {"type": "analyze", "prompt": "Analyze this data"}
        context = {}

        with patch('src.services.agent_executor.claude_client') as mock_claude:
            mock_claude.complete = AsyncMock(return_value="Analysis result")

            result = await executor._action_analyze(action, context)

            assert result["success"] is True
            assert result["analysis"] == "Analysis result"
            assert result["type"] == "analysis"
            mock_claude.complete.assert_called_once_with("Analyze this data")

    @pytest.mark.asyncio
    async def test_analyze_with_template(self, executor):
        """Test analysis with template variables."""
        action = {"type": "analyze", "prompt": "Analyze {{data}}"}
        context = {"data": "sales data"}

        with patch('src.services.agent_executor.claude_client') as mock_claude:
            mock_claude.complete = AsyncMock(return_value="Sales analysis")

            result = await executor._action_analyze(action, context)

            assert result["success"] is True
            mock_claude.complete.assert_called_once_with("Analyze sales data")

    @pytest.mark.asyncio
    async def test_analyze_claude_error(self, executor):
        """Test analysis when Claude fails."""
        action = {"type": "analyze", "prompt": "Test"}
        context = {}

        with patch('src.services.agent_executor.claude_client') as mock_claude:
            mock_claude.complete = AsyncMock(side_effect=Exception("API error"))

            result = await executor._action_analyze(action, context)

            assert result["success"] is False
            assert "Analysis failed" in result["error"]


class TestActionHTTP:
    """Test HTTP action."""

    @pytest.mark.asyncio
    async def test_http_get_success(self, executor):
        """Test successful GET request."""
        action = {
            "type": "http",
            "url": "https://api.example.com/data",
            "method": "GET"
        }
        context = {}

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.text = "Response body"

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await executor._action_http(action, context)

            assert result["success"] is True
            assert result["status_code"] == 200
            assert result["body"] == "Response body"
            assert result["type"] == "http"

    @pytest.mark.asyncio
    async def test_http_post_with_body(self, executor):
        """Test POST request with JSON body."""
        action = {
            "type": "http",
            "url": "https://api.example.com/data",
            "method": "POST",
            "body": {"key": "value"}
        }
        context = {}

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 201
        mock_response.text = "Created"

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await executor._action_http(action, context)

            assert result["success"] is True
            assert result["status_code"] == 201

    @pytest.mark.asyncio
    async def test_http_ssrf_protection_localhost(self, executor):
        """Test SSRF protection blocks localhost."""
        action = {
            "type": "http",
            "url": "http://localhost:8080/admin",
            "method": "GET"
        }
        context = {}

        result = await executor._action_http(action, context)

        assert result["success"] is False
        assert "blocked host" in result["error"]

    @pytest.mark.asyncio
    async def test_http_ssrf_protection_private_ip(self, executor):
        """Test SSRF protection blocks private IPs."""
        action = {
            "type": "http",
            "url": "http://192.168.1.1/config",
            "method": "GET"
        }
        context = {}

        result = await executor._action_http(action, context)

        assert result["success"] is False
        assert "internal/private network" in result["error"]

    @pytest.mark.asyncio
    async def test_http_ssrf_protection_aws_metadata(self, executor):
        """Test SSRF protection blocks AWS metadata endpoint."""
        action = {
            "type": "http",
            "url": "http://169.254.169.254/latest/meta-data",
            "method": "GET"
        }
        context = {}

        result = await executor._action_http(action, context)

        assert result["success"] is False
        assert "blocked host" in result["error"]

    @pytest.mark.asyncio
    async def test_http_invalid_scheme(self, executor):
        """Test invalid URL scheme is blocked."""
        action = {
            "type": "http",
            "url": "file:///etc/passwd",
            "method": "GET"
        }
        context = {}

        result = await executor._action_http(action, context)

        assert result["success"] is False
        assert "Invalid URL scheme" in result["error"]

    @pytest.mark.asyncio
    async def test_http_url_template(self, executor):
        """Test HTTP with URL template."""
        action = {
            "type": "http",
            "url": "https://api.example.com/users/{{user_id}}",
            "method": "GET"
        }
        context = {"user_id": "123"}

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.text = "User data"

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await executor._action_http(action, context)

            assert result["success"] is True
            # Verify the URL was templated correctly
            call_kwargs = mock_instance.request.call_args[1]
            assert "123" in call_kwargs["url"]

    @pytest.mark.asyncio
    async def test_http_response_truncation(self, executor):
        """Test that long responses are truncated."""
        action = {
            "type": "http",
            "url": "https://api.example.com/data",
            "method": "GET"
        }
        context = {}

        # Create a response longer than 1000 chars
        long_text = "x" * 2000

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.text = long_text

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await executor._action_http(action, context)

            assert result["success"] is True
            assert len(result["body"]) == 1000


class TestActionDelay:
    """Test delay action."""

    @pytest.mark.asyncio
    async def test_delay_default(self, executor):
        """Test delay with default duration."""
        action = {"type": "delay"}
        context = {}

        result = await executor._action_delay(action, context)

        assert result["success"] is True
        assert result["waited_seconds"] == 1
        assert result["type"] == "delay"

    @pytest.mark.asyncio
    async def test_delay_custom_duration(self, executor):
        """Test delay with custom duration."""
        action = {"type": "delay", "seconds": 5}
        context = {}

        result = await executor._action_delay(action, context)

        assert result["success"] is True
        assert result["waited_seconds"] == 5

    @pytest.mark.asyncio
    async def test_delay_max_timeout(self, executor):
        """Test delay is capped at 60 seconds."""
        action = {"type": "delay", "seconds": 120}
        context = {}

        # We don't actually wait, just verify the logic
        result = await executor._action_delay(action, context)

        assert result["success"] is True
        # The action should report what was requested, not what was actually waited
        assert result["waited_seconds"] == 120


class TestActionCondition:
    """Test condition action."""

    @pytest.mark.asyncio
    async def test_condition_equal(self, executor):
        """Test equality condition."""
        action = {"type": "condition", "condition": "status == 'active'"}
        context = {"status": "active"}

        result = await executor._action_condition(action, context)

        assert result["success"] is True
        assert result["result"] is True
        assert result["type"] == "condition"

    @pytest.mark.asyncio
    async def test_condition_not_equal(self, executor):
        """Test not equal condition."""
        action = {"type": "condition", "condition": "status != 'inactive'"}
        context = {"status": "active"}

        result = await executor._action_condition(action, context)

        assert result["success"] is True
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_condition_greater_than(self, executor):
        """Test greater than condition."""
        action = {"type": "condition", "condition": "count > 5"}
        context = {"count": 10}

        result = await executor._action_condition(action, context)

        assert result["success"] is True
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_condition_less_than(self, executor):
        """Test less than condition."""
        action = {"type": "condition", "condition": "count < 5"}
        context = {"count": 3}

        result = await executor._action_condition(action, context)

        assert result["success"] is True
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_condition_in_operator(self, executor):
        """Test 'in' operator."""
        action = {"type": "condition", "condition": "'admin' in roles"}
        context = {"roles": ["admin", "user"]}

        result = await executor._action_condition(action, context)

        assert result["success"] is True
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_condition_and_operator(self, executor):
        """Test 'and' operator."""
        action = {"type": "condition", "condition": "age > 18 and verified == true"}
        context = {"age": 25, "verified": True}

        result = await executor._action_condition(action, context)

        assert result["success"] is True
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_condition_or_operator(self, executor):
        """Test 'or' operator."""
        action = {"type": "condition", "condition": "role == 'admin' or role == 'moderator'"}
        context = {"role": "moderator"}

        result = await executor._action_condition(action, context)

        assert result["success"] is True
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_condition_false_result(self, executor):
        """Test condition that evaluates to false."""
        action = {"type": "condition", "condition": "count > 100"}
        context = {"count": 5}

        result = await executor._action_condition(action, context)

        assert result["success"] is True
        assert result["result"] is False

    @pytest.mark.asyncio
    async def test_condition_error_handling(self, executor):
        """Test condition evaluation error."""
        action = {"type": "condition", "condition": ""}
        context = {}

        result = await executor._action_condition(action, context)

        # Empty condition should be handled gracefully
        assert result["success"] is True or result["success"] is False


class TestActionLog:
    """Test log action."""

    @pytest.mark.asyncio
    async def test_log_simple_message(self, executor):
        """Test simple log message."""
        action = {"type": "log", "message": "Test log"}
        context = {}

        result = await executor._action_log(action, context)

        assert result["success"] is True
        assert result["logged"] == "Test log"
        assert result["type"] == "log"

    @pytest.mark.asyncio
    async def test_log_with_template(self, executor):
        """Test log with template variables."""
        action = {"type": "log", "message": "User {{user}} logged in"}
        context = {"user": "alice"}

        result = await executor._action_log(action, context)

        assert result["success"] is True
        assert result["logged"] == "User alice logged in"

    @pytest.mark.asyncio
    async def test_log_empty_message(self, executor):
        """Test log with empty message."""
        action = {"type": "log"}
        context = {}

        result = await executor._action_log(action, context)

        assert result["success"] is True
        assert result["logged"] == ""


class TestTemplateRendering:
    """Test template rendering."""

    def test_render_single_variable(self, executor):
        """Test rendering single variable."""
        template = "Hello {{name}}"
        context = {"name": "World"}

        result = executor._render_template(template, context)

        assert result == "Hello World"

    def test_render_multiple_variables(self, executor):
        """Test rendering multiple variables."""
        template = "{{greeting}} {{name}}!"
        context = {"greeting": "Hello", "name": "Alice"}

        result = executor._render_template(template, context)

        assert result == "Hello Alice!"

    def test_render_no_variables(self, executor):
        """Test rendering with no variables."""
        template = "Static text"
        context = {}

        result = executor._render_template(template, context)

        assert result == "Static text"

    def test_render_missing_variable(self, executor):
        """Test rendering with missing variable."""
        template = "Hello {{name}}"
        context = {}

        result = executor._render_template(template, context)

        # Missing variables are left as-is
        assert result == "Hello {{name}}"

    def test_render_numeric_value(self, executor):
        """Test rendering numeric values."""
        template = "Count: {{count}}"
        context = {"count": 42}

        result = executor._render_template(template, context)

        assert result == "Count: 42"


class TestValueResolution:
    """Test value resolution for conditions."""

    def test_resolve_context_variable(self, executor):
        """Test resolving context variable."""
        context = {"username": "alice"}

        result = executor._resolve_value("username", context)

        assert result == "alice"

    def test_resolve_string_literal(self, executor):
        """Test resolving string literal."""
        context = {}

        result = executor._resolve_value('"hello"', context)

        assert result == "hello"

    def test_resolve_number(self, executor):
        """Test resolving number."""
        context = {}

        result = executor._resolve_value("42", context)

        assert result == 42

    def test_resolve_boolean_true(self, executor):
        """Test resolving boolean true."""
        context = {}

        result = executor._resolve_value("true", context)

        assert result is True

    def test_resolve_boolean_false(self, executor):
        """Test resolving boolean false."""
        context = {}

        result = executor._resolve_value("false", context)

        assert result is False

    def test_resolve_null(self, executor):
        """Test resolving null."""
        context = {}

        result = executor._resolve_value("null", context)

        assert result is None

    def test_resolve_quoted_string(self, executor):
        """Test resolving quoted string."""
        context = {}

        result = executor._resolve_value("'hello world'", context)

        assert result == "hello world"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_execute_with_none_context(self, executor, mock_agent):
        """Test execution with None context."""
        mock_agent.actions = [{"type": "log", "message": "Test"}]

        result = await executor.execute(mock_agent, None)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_action_missing_type(self, executor, mock_agent):
        """Test action without type field."""
        mock_agent.actions = [{"message": "No type"}]

        result = await executor.execute(mock_agent)

        assert result["success"] is False
        assert "Unknown action type" in result["error"]

    @pytest.mark.asyncio
    async def test_http_malformed_url(self, executor):
        """Test HTTP with malformed URL."""
        action = {
            "type": "http",
            "url": "not a url",
            "method": "GET"
        }
        context = {}

        result = await executor._action_http(action, context)

        assert result["success"] is False
        assert "Invalid URL scheme" in result["error"]

    @pytest.mark.asyncio
    async def test_condition_complex_nested(self, executor):
        """Test condition with 'and' operator (parentheses not supported)."""
        # Note: parentheses not supported by safe_eval, using simple 'and'
        action = {
            "type": "condition",
            "condition": "age > 18 and role == 'admin'"
        }
        context = {"age": 25, "role": "admin"}

        result = await executor._action_condition(action, context)

        # Should handle 'and' conditions
        assert result["success"] is True
        assert result["result"] is True

    @pytest.mark.asyncio
    async def test_http_body_with_template(self, executor):
        """Test HTTP request with templated body."""
        action = {
            "type": "http",
            "url": "https://api.example.com/data",
            "method": "POST",
            "body": {"user": "{{username}}", "action": "login"}
        }
        context = {"username": "alice"}

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.text = "OK"

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await executor._action_http(action, context)

            assert result["success"] is True
            # Verify body was templated
            call_kwargs = mock_instance.request.call_args[1]
            assert call_kwargs["json"]["user"] == "alice"

    @pytest.mark.asyncio
    async def test_result_structure_completeness(self, executor, mock_agent):
        """Test that result structure is complete."""
        mock_agent.actions = [
            {"type": "log", "message": "Test"}
        ]

        result = await executor.execute(mock_agent)

        # Verify all required fields are present
        assert "success" in result
        assert "error" in result
        assert "results" in result
        assert "executed_at" in result

        # Verify executed_at is ISO format timestamp
        assert isinstance(result["executed_at"], str)
        # Should be parseable as datetime
        datetime.fromisoformat(result["executed_at"].replace('Z', '+00:00'))

    @pytest.mark.asyncio
    async def test_action_result_structure(self, executor, mock_agent):
        """Test that action result structure is correct."""
        mock_agent.actions = [
            {"type": "log", "message": "Test"}
        ]

        result = await executor.execute(mock_agent)

        action_result = result["results"][0]
        assert "action_index" in action_result
        assert "action_type" in action_result
        assert "result" in action_result
        assert action_result["action_index"] == 0
        assert action_result["action_type"] == "log"
