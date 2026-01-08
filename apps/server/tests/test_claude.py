"""Tests for Claude client - direct Anthropic API."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.claude import ClaudeClient, ClaudeClientError


@pytest.fixture
def claude_client():
    """Create Claude client with mocked settings."""
    with patch('src.core.claude.settings') as mock_settings:
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_settings.claude_model = "claude-sonnet-4-20250514"
        yield ClaudeClient()


@pytest.fixture
def claude_client_no_key():
    """Create Claude client without API key."""
    with patch('src.core.claude.settings') as mock_settings:
        mock_settings.anthropic_api_key = ""
        mock_settings.claude_model = "claude-sonnet-4-20250514"
        yield ClaudeClient()


class TestClaudeClient:
    """Test cases for ClaudeClient."""

    def test_headers_include_api_key(self, claude_client):
        """Test that x-api-key header is included when key is set."""
        headers = claude_client._get_headers()
        assert headers["x-api-key"] == "sk-ant-test-key"
        assert headers["Content-Type"] == "application/json"
        assert headers["anthropic-version"] == "2023-06-01"

    def test_base_url_is_anthropic(self, claude_client):
        """Test that base URL points to Anthropic API."""
        assert claude_client.base_url == "https://api.anthropic.com"

    @pytest.mark.asyncio
    async def test_complete_fails_without_api_key(self, claude_client_no_key):
        """Test that complete fails when API key is not configured."""
        with pytest.raises(ClaudeClientError) as exc:
            await claude_client_no_key.complete("Test prompt")
        assert "ANTHROPIC_API_KEY not configured" in str(exc.value)

    @pytest.mark.asyncio
    async def test_complete_fails_without_prompt_or_messages(self, claude_client):
        """Test that complete fails when neither prompt nor messages provided."""
        with pytest.raises(ClaudeClientError) as exc:
            await claude_client.complete()
        assert "Either 'prompt' or 'messages' must be provided" in str(exc.value)

    @pytest.mark.asyncio
    async def test_complete_success_with_prompt(self, claude_client):
        """Test successful completion with prompt."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Hello, world!"}],
            "role": "assistant"
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await claude_client.complete("Test prompt")
            assert result == "Hello, world!"

            # Verify request was made to correct endpoint
            call_args = mock_instance.post.call_args
            assert call_args[0][0] == "https://api.anthropic.com/v1/messages"

    @pytest.mark.asyncio
    async def test_complete_success_with_messages(self, claude_client):
        """Test successful completion with messages array."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Response text"}],
            "role": "assistant"
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"},
            ]
            result = await claude_client.complete(messages=messages)
            assert result == "Response text"

    @pytest.mark.asyncio
    async def test_complete_invalid_response_no_content(self, claude_client):
        """Test error handling for missing content field."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"role": "assistant"}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            with pytest.raises(ClaudeClientError) as exc:
                await claude_client.complete("Test prompt")
            assert "missing 'content' field" in str(exc.value)

    @pytest.mark.asyncio
    async def test_complete_invalid_response_empty_content(self, claude_client):
        """Test error handling for empty content array."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": []}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            with pytest.raises(ClaudeClientError) as exc:
                await claude_client.complete("Test prompt")
            assert "empty or not a list" in str(exc.value)

    @pytest.mark.asyncio
    async def test_complete_invalid_response_no_text(self, claude_client):
        """Test error handling for missing text in content."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"type": "image"}]}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            with pytest.raises(ClaudeClientError) as exc:
                await claude_client.complete("Test prompt")
            assert "missing 'text' in content" in str(exc.value)

    @pytest.mark.asyncio
    async def test_complete_timeout(self, claude_client):
        """Test timeout handling."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            with pytest.raises(ClaudeClientError) as exc:
                await claude_client.complete("Test prompt")
            assert "timed out" in str(exc.value)

    @pytest.mark.asyncio
    async def test_complete_http_error(self, claude_client):
        """Test HTTP error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Error", request=MagicMock(), response=mock_response
                )
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            with pytest.raises(ClaudeClientError) as exc:
                await claude_client.complete("Test prompt")
            assert "500" in str(exc.value)

    @pytest.mark.asyncio
    async def test_complete_with_custom_model(self, claude_client):
        """Test completion with custom model."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Custom model response"}],
            "role": "assistant"
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await claude_client.complete(
                prompt="Test",
                model="claude-opus-4-20250514"
            )
            assert result == "Custom model response"

            # Verify custom model was passed
            call_args = mock_instance.post.call_args
            assert call_args[1]["json"]["model"] == "claude-opus-4-20250514"


class TestAnalyzePatterns:
    """Test cases for analyze_patterns method."""

    @pytest.mark.asyncio
    async def test_analyze_patterns_success(self, claude_client):
        """Test successful pattern analysis."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{
                "type": "text",
                "text": '{"observations": ["obs1"], "automations": [], "suggestions": []}'
            }],
            "role": "assistant"
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await claude_client.analyze_patterns([{"pattern": "test"}])
            assert result["observations"] == ["obs1"]

    @pytest.mark.asyncio
    async def test_analyze_patterns_invalid_json(self, claude_client):
        """Test pattern analysis with invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Not valid JSON"}],
            "role": "assistant"
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await claude_client.analyze_patterns([])
            assert result == {"observations": [], "automations": [], "suggestions": []}


class TestGenerateAgentCode:
    """Test cases for generate_agent_code method."""

    @pytest.mark.asyncio
    async def test_generate_agent_code_success(self, claude_client):
        """Test successful agent code generation."""
        expected_code = "async def agent_task(): pass"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": expected_code}],
            "role": "assistant"
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await claude_client.generate_agent_code(
                agent_type="monitor",
                trigger_config={"schedule": "0 * * * *"},
                actions=[{"type": "notify"}]
            )
            assert result == expected_code
