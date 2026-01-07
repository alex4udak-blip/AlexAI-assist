# Quick Start Guide for API Tests

## Installation

```bash
cd apps/server
pip install -e ".[dev]"
```

## Run All Tests

```bash
pytest tests/test_api.py -v
```

Expected output:
```
tests/test_api.py::TestHealthEndpoints::test_health_check PASSED
tests/test_api.py::TestHealthEndpoints::test_readiness_check_success PASSED
tests/test_api.py::TestChatEndpoints::test_send_message_success PASSED
...
================================================ 47 passed in 2.5s ================================================
```

## Run Specific Test Categories

### Health Checks
```bash
pytest tests/test_api.py::TestHealthEndpoints -v
```

### Chat Endpoints
```bash
pytest tests/test_api.py::TestChatEndpoints -v
```

### Event Endpoints
```bash
pytest tests/test_api.py::TestEventEndpoints -v
```

### Agent Endpoints
```bash
pytest tests/test_api.py::TestAgentEndpoints -v
```

### Memory Endpoints
```bash
pytest tests/test_api.py::TestMemoryEndpoints -v
```

## Run Individual Tests

### Test sending a chat message
```bash
pytest tests/test_api.py::TestChatEndpoints::test_send_message_success -v
```

### Test creating events
```bash
pytest tests/test_api.py::TestEventEndpoints::test_create_events_success -v
```

### Test agent CRUD operations
```bash
pytest tests/test_api.py::TestAgentEndpoints::test_create_agent_success -v
```

## Run with Coverage

```bash
pytest tests/test_api.py --cov=src.api.routes --cov-report=html
```

Then open `htmlcov/index.html` in a browser to see detailed coverage.

## Run with Different Output Formats

### Minimal output
```bash
pytest tests/test_api.py -q
```

### Very verbose with test details
```bash
pytest tests/test_api.py -vv
```

### Show print statements
```bash
pytest tests/test_api.py -s
```

### Show test durations
```bash
pytest tests/test_api.py --durations=10
```

## Debugging Failed Tests

### Run only failed tests from last run
```bash
pytest tests/test_api.py --lf
```

### Run failed tests first, then others
```bash
pytest tests/test_api.py --ff
```

### Stop on first failure
```bash
pytest tests/test_api.py -x
```

### Drop into debugger on failure
```bash
pytest tests/test_api.py --pdb
```

## Run Tests Matching Pattern

### All tests with "chat" in the name
```bash
pytest tests/test_api.py -k "chat" -v
```

### All tests with "create" in the name
```bash
pytest tests/test_api.py -k "create" -v
```

### All async tests
```bash
pytest tests/test_api.py -k "async" -v
```

## Continuous Integration

For CI/CD pipelines:

```bash
pytest tests/test_api.py \
  --cov=src.api.routes \
  --cov-report=xml \
  --cov-report=term-missing \
  --cov-fail-under=80 \
  -v
```

## Troubleshooting

### ModuleNotFoundError
```bash
# Ensure you're in the right directory
cd apps/server

# Install in editable mode
pip install -e ".[dev]"
```

### Import errors
```bash
# Add PYTHONPATH
export PYTHONPATH=/home/user/AlexAI-assist/apps/server:$PYTHONPATH
pytest tests/test_api.py
```

### Database errors
Tests use SQLite in-memory database. If you see errors:
```bash
# Ensure aiosqlite is installed
pip install aiosqlite
```

## Test Examples

### Example 1: Testing Chat Endpoint
```python
def test_send_message_success(self, client: TestClient):
    """Test sending a chat message successfully."""
    payload = {
        "message": "Hello, how can you help me?",
        "context": {"session_id": "test-session"}
    }
    
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == payload["message"]
    assert "response" in data
```

### Example 2: Testing Event Creation
```python
async def test_create_events_success(self, client: TestClient):
    """Test creating events successfully."""
    payload = {
        "events": [
            {
                "device_id": "test-device",
                "event_type": "app_activity",
                "timestamp": datetime.utcnow().isoformat(),
                "app_name": "Chrome",
                "category": "browsing"
            }
        ]
    }
    
    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 200
    assert response.json()["created"] == 1
```

### Example 3: Testing Error Handling
```python
def test_get_agent_not_found(self, client: TestClient):
    """Test getting non-existent agent."""
    fake_id = uuid4()
    response = client.get(f"/api/v1/agents/{fake_id}")
    assert response.status_code == 404
```

## Next Steps

1. Run all tests to ensure they pass
2. Review test coverage report
3. Add more tests for edge cases as needed
4. Integrate into CI/CD pipeline
5. Monitor test execution times

For more details, see:
- `README.md` - Full documentation
- `IMPLEMENTATION_SUMMARY.md` - Detailed implementation notes
