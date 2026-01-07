# Observer Server Tests

Comprehensive test suite for the Observer API server.

## Setup

Install test dependencies:

```bash
pip install -e ".[dev]"
```

Or install directly:

```bash
pip install pytest pytest-asyncio pytest-cov aiosqlite
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_api.py
```

### Run specific test class
```bash
pytest tests/test_api.py::TestChatEndpoints
```

### Run specific test
```bash
pytest tests/test_api.py::TestChatEndpoints::test_send_message_success
```

### Run with coverage
```bash
pytest --cov=src --cov-report=html
```

### Run with verbose output
```bash
pytest -v
```

### Run async tests only
```bash
pytest -m asyncio
```

## Test Structure

### test_api.py
Comprehensive API endpoint tests covering:

1. **Health Check Endpoints**
   - `/health` - Basic health check
   - `/ready` - Readiness check with DB connectivity
   - `/` - Root endpoint

2. **Chat Endpoints** (`/api/v1/chat`)
   - POST `/` - Send chat message
   - GET `/history` - Get chat history
   - DELETE `/history` - Clear chat history
   - Tests for success cases, validation errors, and edge cases

3. **Event Endpoints** (`/api/v1/events`)
   - POST `/` - Create events (batch)
   - GET `/` - Get events with filters
   - GET `/timeline` - Get activity timeline
   - Tests for pagination, filters, and data validation

4. **Agent Endpoints** (`/api/v1/agents`)
   - GET `/` - List agents
   - POST `/` - Create agent
   - GET `/{id}` - Get specific agent
   - PATCH `/{id}` - Update agent
   - DELETE `/{id}` - Delete agent
   - POST `/{id}/enable` - Enable agent
   - POST `/{id}/disable` - Disable agent
   - Tests for CRUD operations and status management

5. **Suggestion Endpoints** (`/api/v1/suggestions`)
   - GET `/` - List suggestions
   - POST `/` - Create suggestion
   - POST `/{id}/dismiss` - Dismiss suggestion
   - Tests for filtering and lifecycle management

6. **Memory Endpoints** (`/api/v1/memory`)
   - GET `/context` - Get memory context
   - GET `/stats` - Get memory statistics
   - POST `/facts` - Add fact
   - GET `/facts` - List facts
   - POST `/facts/search` - Search facts
   - GET `/persona` - Get user persona
   - POST `/consolidate` - Trigger consolidation
   - Tests with mocked MemoryManager

7. **Error Handling**
   - 404 on invalid endpoints
   - 405 on wrong HTTP methods
   - 422 on validation errors
   - Invalid UUID handling

8. **Rate Limiting**
   - Tests for rate limit enforcement
   - Rate limit header validation

## Test Fixtures

- `test_db_engine` - In-memory SQLite database for testing
- `test_db_session` - Database session with automatic rollback
- `client` - FastAPI TestClient with mocked dependencies

## Mocked Dependencies

The tests mock the following external dependencies:
- Claude AI client (`claude_client`)
- Redis cache (`get_redis`)
- AnalyzerService
- MemoryManager
- WebSocket broadcast

This ensures tests run quickly and don't depend on external services.

## Writing New Tests

When adding new tests:

1. Use the existing fixtures for database and client
2. Mock external dependencies appropriately
3. Test both success and error cases
4. Use `@pytest.mark.asyncio` for async tests
5. Clean up test data in fixtures
6. Follow the existing test structure

Example:

```python
@pytest.mark.asyncio
async def test_new_endpoint(self, client: TestClient, test_db_session: AsyncSession):
    """Test description."""
    # Setup test data
    test_data = {...}

    # Make request
    response = client.post("/api/v1/endpoint", json=test_data)

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["field"] == expected_value
```

## Continuous Integration

Tests should be run in CI/CD pipeline before deployment:

```bash
pytest --cov=src --cov-report=xml --cov-fail-under=80
```

## Troubleshooting

### Import Errors
Ensure you're in the correct directory and dependencies are installed:
```bash
cd apps/server
pip install -e ".[dev]"
```

### Async Test Failures
Check pytest-asyncio configuration in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Database Errors
Tests use SQLite in-memory database. If you see SQLAlchemy errors, check:
- Model definitions are compatible with SQLite
- Foreign key constraints are properly defined
- Async operations use `await`
