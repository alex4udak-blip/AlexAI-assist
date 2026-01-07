"""Tests for Claude client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.claude import ClaudeClient, ClaudeClientError


@pytest.fixture
def claude_client():
    """Create Claude client with mocked settings."""
    with patch('src.core.claude.settings') as mock_settings:
        mock_settings.claude_proxy_url = "http://test-proxy:3001"
        mock_settings.ccproxy_internal_token = "test-token"
        mock_settings.claude_model = "claude-sonnet-4-20250514"
        yield ClaudeClient()


class TestClaudeClient:
    """Test cases for ClaudeClient."""

    def test_headers_include_auth_when_token_set(self, claude_client):
        """Test that auth header is included when token is set."""
        headers = claude_client._get_headers()
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"

    def test_headers_no_auth_when_no_token(self):
        """Test that auth header is omitted when no token."""
        with patch('src.core.claude.settings') as mock_settings:
            mock_settings.claude_proxy_url = "http://test-proxy:3001"
            mock_settings.ccproxy_internal_token = ""
            mock_settings.claude_model = "claude-sonnet-4-20250514"
            client = ClaudeClient()
            headers = client._get_headers()
            assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_complete_success(self, claude_client):
        """Test successful completion."""
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
