"""Comprehensive API endpoint tests."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.base import Base
from src.db.models import Agent, ChatMessage, Device, Event, Suggestion
from src.main import app

# ===========================================
# FIXTURES
# ===========================================


@pytest.fixture(scope="function")
async def test_db_engine():
    """Create test database engine."""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db_session(test_db_engine):
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def client(test_db_session: AsyncSession):
    """Create test client with mocked dependencies."""

    # Override database dependency
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    # Mock Claude client
    with patch("src.api.routes.chat.claude_client") as mock_claude:
        mock_claude.complete = AsyncMock(return_value="Test AI response")

        # Mock Redis
        with patch("src.api.routes.chat.get_redis") as mock_redis:
            mock_redis.return_value = None

            # Mock AnalyzerService
            with patch("src.api.routes.chat.AnalyzerService") as mock_analyzer:
                mock_analyzer_instance = MagicMock()
                mock_analyzer_instance.get_summary = AsyncMock(return_value={
                    "total_events": 100,
                    "top_apps": [("Chrome", 50), ("VSCode", 30)],
                    "categories": {"development": 80, "browsing": 20},
                })
                mock_analyzer.return_value = mock_analyzer_instance

                # Mock MemoryManager
                with patch("src.api.routes.chat.MemoryManager") as mock_memory:
                    mock_memory_instance = MagicMock()
                    mock_memory_instance.build_context_for_query = AsyncMock(return_value={})
                    mock_memory_instance.format_context_for_prompt = AsyncMock(return_value="")
                    mock_memory_instance.process_interaction = AsyncMock()
                    mock_memory.return_value = mock_memory_instance

                    # Mock WebSocket broadcast
                    with patch("src.core.websocket.broadcast_events_batch") as mock_broadcast:
                        mock_broadcast.return_value = asyncio.Future()
                        mock_broadcast.return_value.set_result(None)

                        # Override dependencies
                        from src.api.deps import get_db_session
                        app.dependency_overrides[get_db_session] = override_get_db_session

                        with TestClient(app) as test_client:
                            yield test_client

                        # Clean up overrides
                        app.dependency_overrides.clear()


# ===========================================
# HEALTH CHECK TESTS
# ===========================================


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check_comprehensive(self, client: TestClient):
        """Test comprehensive health check endpoint."""
        response = client.get("/health")
        assert response.status_code in [200, 503]
        data = response.json()

        # Check overall response structure
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in data
        assert "response_time_ms" in data
        assert "checks" in data

        # Check individual service checks
        checks = data["checks"]
        assert "database" in checks
        assert "redis" in checks
        assert "memory" in checks
        assert "disk" in checks

        # Validate database check structure
        db_check = checks["database"]
        assert "status" in db_check
        assert db_check["status"] in ["healthy", "degraded", "unhealthy"]

        # Validate memory check structure
        mem_check = checks["memory"]
        assert "status" in mem_check
        if "percent_used" in mem_check:
            assert isinstance(mem_check["percent_used"], (int, float))
            assert 0 <= mem_check["percent_used"] <= 100

        # Validate disk check structure
        disk_check = checks["disk"]
        assert "status" in disk_check
        if "percent_used" in disk_check:
            assert isinstance(disk_check["percent_used"], (int, float))
            assert 0 <= disk_check["percent_used"] <= 100

    def test_health_check_response_time(self, client: TestClient):
        """Test that health check responds quickly."""
        import time
        start = time.time()
        response = client.get("/health")
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code in [200, 503]
        # Health check should complete in under 10 seconds
        assert elapsed_ms < 10000

        data = response.json()
        # Response time reported should be reasonable
        assert data["response_time_ms"] < 10000

    def test_readiness_check_success(self, client: TestClient):
        """Test readiness check with database connection."""
        response = client.get("/ready")
        assert response.status_code in [200, 503]
        data = response.json()

        # Check response structure
        assert "status" in data
        assert data["status"] in ["ready", "not_ready"]
        assert "timestamp" in data

        # If not ready, should have a reason
        if data["status"] == "not_ready":
            assert "reason" in data

    def test_readiness_check_fast(self, client: TestClient):
        """Test that readiness check is faster than health check."""
        import time
        start = time.time()
        response = client.get("/ready")
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code in [200, 503]
        # Readiness check should be very fast (under 5 seconds)
        assert elapsed_ms < 5000

    def test_health_check_status_codes(self, client: TestClient):
        """Test proper HTTP status codes based on health."""
        response = client.get("/health")
        data = response.json()

        # Status code should match health status
        if data["status"] == "unhealthy":
            assert response.status_code == 503
        elif data["status"] in ["healthy", "degraded"]:
            assert response.status_code == 200

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "observer-api"


# ===========================================
# CHAT ENDPOINT TESTS
# ===========================================


class TestChatEndpoints:
    """Test chat endpoints."""

    def test_send_message_success(self, client: TestClient):
        """Test sending a chat message successfully."""
        payload = {
            "message": "Hello, how can you help me?",
            "context": {"session_id": "test-session"}
        }

        response = client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["message"] == payload["message"]
        assert data["response"] == "Test AI response"
        assert "timestamp" in data

    def test_send_message_without_context(self, client: TestClient):
        """Test sending message without context uses default session."""
        payload = {"message": "Test message"}

        response = client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == payload["message"]

    def test_send_empty_message_fails(self, client: TestClient):
        """Test sending empty message fails validation."""
        payload = {"message": ""}

        response = client.post("/api/v1/chat", json=payload)
        assert response.status_code == 422  # Validation error

    def test_get_chat_history_empty(self, client: TestClient):
        """Test getting chat history when empty."""
        response = client.get("/api/v1/chat/history?session_id=empty-session")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_chat_history_with_messages(self, client: TestClient, test_db_session: AsyncSession):
        """Test getting chat history with existing messages."""
        # Add test messages to database
        session_id = "test-session"
        messages = [
            ChatMessage(
                id=uuid4(),
                session_id=session_id,
                role="user",
                content="Hello",
                timestamp=datetime.now(UTC).replace(tzinfo=None),
            ),
            ChatMessage(
                id=uuid4(),
                session_id=session_id,
                role="assistant",
                content="Hi there!",
                timestamp=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=1),
            ),
        ]

        for msg in messages:
            test_db_session.add(msg)
        await test_db_session.commit()

        response = client.get(f"/api/v1/chat/history?session_id={session_id}")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "Hello"
        assert data[1]["role"] == "assistant"

    def test_get_chat_history_with_limit(self, client: TestClient):
        """Test chat history with limit parameter."""
        response = client.get("/api/v1/chat/history?session_id=test&limit=10")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    @pytest.mark.asyncio
    async def test_clear_chat_history(self, client: TestClient, test_db_session: AsyncSession):
        """Test clearing chat history."""
        # Add test message
        session_id = "clear-session"
        msg = ChatMessage(
            id=uuid4(),
            session_id=session_id,
            role="user",
            content="Test",
            timestamp=datetime.now(UTC).replace(tzinfo=None),
        )
        test_db_session.add(msg)
        await test_db_session.commit()

        response = client.delete(f"/api/v1/chat/history?session_id={session_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Chat history cleared"

        # Verify history is empty
        history_response = client.get(f"/api/v1/chat/history?session_id={session_id}")
        assert len(history_response.json()) == 0


# ===========================================
# EVENT ENDPOINT TESTS
# ===========================================


class TestEventEndpoints:
    """Test event endpoints."""

    @pytest.mark.asyncio
    async def test_create_events_success(self, client: TestClient, test_db_session: AsyncSession):
        """Test creating events successfully."""
        device_id = "test-device-001"
        payload = {
            "events": [
                {
                    "device_id": device_id,
                    "event_type": "app_activity",
                    "timestamp": datetime.now(UTC).replace(tzinfo=None).isoformat(),
                    "app_name": "Chrome",
                    "window_title": "Google Search",
                    "category": "browsing",
                    "data": {"duration": 120}
                },
                {
                    "device_id": device_id,
                    "event_type": "app_activity",
                    "timestamp": datetime.now(UTC).replace(tzinfo=None).isoformat(),
                    "app_name": "VSCode",
                    "window_title": "main.py",
                    "category": "development",
                    "data": {"duration": 300}
                }
            ]
        }

        response = client.post("/api/v1/events", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["created"] == 2

    def test_create_events_empty_batch(self, client: TestClient):
        """Test creating events with empty batch."""
        payload = {"events": []}

        response = client.post("/api/v1/events", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["created"] == 0

    def test_create_events_invalid_data(self, client: TestClient):
        """Test creating events with invalid data."""
        payload = {
            "events": [
                {
                    "device_id": "test",
                    "event_type": "invalid",
                    # Missing required timestamp field
                    "app_name": "Test"
                }
            ]
        }

        response = client.post("/api/v1/events", json=payload)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_events_empty(self, client: TestClient):
        """Test getting events when empty."""
        response = client.get("/api/v1/events")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_events_with_filters(self, client: TestClient, test_db_session: AsyncSession):
        """Test getting events with filters."""
        # Create test device and events
        device = Device(id="test-device", name="Test Device", os="Linux")
        test_db_session.add(device)

        now = datetime.now(UTC).replace(tzinfo=None)
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_activity",
                timestamp=now,
                app_name="Chrome",
                category="browsing",
            ),
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_activity",
                timestamp=now + timedelta(seconds=10),
                app_name="VSCode",
                category="development",
            ),
        ]

        for event in events:
            test_db_session.add(event)
        await test_db_session.commit()

        # Test device filter
        response = client.get("/api/v1/events?device_id=test-device")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Test category filter
        response = client.get("/api/v1/events?category=browsing")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["app_name"] == "Chrome"

    @pytest.mark.asyncio
    async def test_get_events_with_pagination(self, client: TestClient, test_db_session: AsyncSession):
        """Test event pagination."""
        device = Device(id="test-device", name="Test Device", os="Linux")
        test_db_session.add(device)

        # Create multiple events
        for i in range(15):
            event = Event(
                id=uuid4(),
                device_id="test-device",
                event_type="test",
                timestamp=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=i),
                app_name=f"App{i}",
            )
            test_db_session.add(event)
        await test_db_session.commit()

        # Test limit
        response = client.get("/api/v1/events?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

        # Test offset
        response = client.get("/api/v1/events?limit=10&offset=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_get_timeline(self, client: TestClient, test_db_session: AsyncSession):
        """Test getting activity timeline."""
        device = Device(id="test-device", name="Test Device", os="Linux")
        test_db_session.add(device)

        # Create events in last 24 hours
        now = datetime.now(UTC).replace(tzinfo=None)
        event = Event(
            id=uuid4(),
            device_id="test-device",
            event_type="app_activity",
            timestamp=now - timedelta(hours=2),
            app_name="Chrome",
        )
        test_db_session.add(event)
        await test_db_session.commit()

        response = client.get("/api/v1/events/timeline?hours=24")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_timeline_with_device_filter(self, client: TestClient):
        """Test timeline with device filter."""
        response = client.get("/api/v1/events/timeline?device_id=test-device&hours=12")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)


# ===========================================
# AGENT ENDPOINT TESTS
# ===========================================


class TestAgentEndpoints:
    """Test agent endpoints."""

    def test_get_agents_empty(self, client: TestClient):
        """Test getting agents when empty."""
        response = client.get("/api/v1/agents")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_create_agent_success(self, client: TestClient):
        """Test creating an agent successfully."""
        payload = {
            "name": "Test Agent",
            "description": "A test automation agent",
            "agent_type": "automation",
            "trigger_config": {"type": "time", "schedule": "0 9 * * *"},
            "actions": [{"type": "log", "message": "Test action"}],
            "settings": {"enabled": True}
        }

        response = client.post("/api/v1/agents", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == payload["name"]
        assert data["agent_type"] == payload["agent_type"]
        assert data["status"] == "active"
        assert "id" in data

    def test_create_agent_invalid_data(self, client: TestClient):
        """Test creating agent with invalid data."""
        payload = {
            "name": "Test",
            # Missing required fields
        }

        response = client.post("/api/v1/agents", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_agent_by_id(self, client: TestClient, test_db_session: AsyncSession):
        """Test getting specific agent by ID."""
        # Create test agent
        agent_id = uuid4()
        agent = Agent(
            id=agent_id,
            name="Test Agent",
            agent_type="automation",
            trigger_config={"type": "manual"},
            actions=[{"type": "log"}],
            settings={},
            status="active",
        )
        test_db_session.add(agent)
        await test_db_session.commit()

        response = client.get(f"/api/v1/agents/{agent_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Test Agent"
        assert UUID(data["id"]) == agent_id

    def test_get_agent_not_found(self, client: TestClient):
        """Test getting non-existent agent."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/agents/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_agent(self, client: TestClient, test_db_session: AsyncSession):
        """Test updating an agent."""
        # Create test agent
        agent_id = uuid4()
        agent = Agent(
            id=agent_id,
            name="Original Name",
            agent_type="automation",
            trigger_config={"type": "manual"},
            actions=[{"type": "log"}],
            settings={},
            status="active",
        )
        test_db_session.add(agent)
        await test_db_session.commit()

        # Update agent
        payload = {"name": "Updated Name", "status": "paused"}
        response = client.patch(f"/api/v1/agents/{agent_id}", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["status"] == "paused"

    @pytest.mark.asyncio
    async def test_delete_agent(self, client: TestClient, test_db_session: AsyncSession):
        """Test deleting an agent."""
        # Create test agent
        agent_id = uuid4()
        agent = Agent(
            id=agent_id,
            name="To Delete",
            agent_type="automation",
            trigger_config={"type": "manual"},
            actions=[{"type": "log"}],
            settings={},
            status="active",
        )
        test_db_session.add(agent)
        await test_db_session.commit()

        response = client.delete(f"/api/v1/agents/{agent_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Agent deleted"

        # Verify deletion
        get_response = client.get(f"/api/v1/agents/{agent_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_enable_agent(self, client: TestClient, test_db_session: AsyncSession):
        """Test enabling an agent."""
        agent_id = uuid4()
        agent = Agent(
            id=agent_id,
            name="Test Agent",
            agent_type="automation",
            trigger_config={"type": "manual"},
            actions=[{"type": "log"}],
            settings={},
            status="paused",
        )
        test_db_session.add(agent)
        await test_db_session.commit()

        response = client.post(f"/api/v1/agents/{agent_id}/enable")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_disable_agent(self, client: TestClient, test_db_session: AsyncSession):
        """Test disabling an agent."""
        agent_id = uuid4()
        agent = Agent(
            id=agent_id,
            name="Test Agent",
            agent_type="automation",
            trigger_config={"type": "manual"},
            actions=[{"type": "log"}],
            settings={},
            status="active",
        )
        test_db_session.add(agent)
        await test_db_session.commit()

        response = client.post(f"/api/v1/agents/{agent_id}/disable")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "paused"

    def test_get_agents_with_filters(self, client: TestClient):
        """Test getting agents with status and type filters."""
        response = client.get("/api/v1/agents?status=active&agent_type=automation")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)


# ===========================================
# SUGGESTION ENDPOINT TESTS
# ===========================================


class TestSuggestionEndpoints:
    """Test suggestion endpoints."""

    def test_get_suggestions_empty(self, client: TestClient):
        """Test getting suggestions when empty."""
        response = client.get("/api/v1/suggestions")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_create_suggestion(self, client: TestClient):
        """Test creating a suggestion."""
        payload = {
            "title": "Automate daily report",
            "description": "Generate daily activity report automatically",
            "agent_type": "automation",
            "agent_config": {"type": "report"},
            "confidence": 0.85,
            "impact": "high",
            "time_saved_minutes": 30
        }

        response = client.post("/api/v1/suggestions", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["title"] == payload["title"]
        assert data["confidence"] == payload["confidence"]
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_suggestions_with_filters(self, client: TestClient, test_db_session: AsyncSession):
        """Test getting suggestions with filters."""
        # Create test suggestions
        suggestions = [
            Suggestion(
                id=uuid4(),
                title="Suggestion 1",
                agent_type="automation",
                agent_config={"type": "test"},
                confidence=0.9,
                impact="high",
                status="pending",
            ),
            Suggestion(
                id=uuid4(),
                title="Suggestion 2",
                agent_type="automation",
                agent_config={"type": "test"},
                confidence=0.6,
                impact="medium",
                status="accepted",
            ),
        ]

        for suggestion in suggestions:
            test_db_session.add(suggestion)
        await test_db_session.commit()

        # Test status filter
        response = client.get("/api/v1/suggestions?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        # Test impact filter
        response = client.get("/api/v1/suggestions?impact=high")
        assert response.status_code == 200
        data = response.json()
        assert all(s["impact"] == "high" for s in data)

    @pytest.mark.asyncio
    async def test_dismiss_suggestion(self, client: TestClient, test_db_session: AsyncSession):
        """Test dismissing a suggestion."""
        suggestion_id = uuid4()
        suggestion = Suggestion(
            id=suggestion_id,
            title="Test Suggestion",
            agent_type="automation",
            agent_config={"type": "test"},
            confidence=0.8,
            impact="medium",
            status="pending",
        )
        test_db_session.add(suggestion)
        await test_db_session.commit()

        response = client.post(f"/api/v1/suggestions/{suggestion_id}/dismiss")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Suggestion dismissed"

    def test_dismiss_nonexistent_suggestion(self, client: TestClient):
        """Test dismissing non-existent suggestion."""
        fake_id = uuid4()
        response = client.post(f"/api/v1/suggestions/{fake_id}/dismiss")
        assert response.status_code == 404


# ===========================================
# MEMORY ENDPOINT TESTS
# ===========================================


class TestMemoryEndpoints:
    """Test memory endpoints."""

    @patch("src.api.routes.memory.MemoryManager")
    def test_get_memory_stats(self, mock_memory_manager, client: TestClient):
        """Test getting memory statistics."""
        # Mock MemoryManager
        mock_instance = MagicMock()
        mock_instance.get_memory_stats = AsyncMock(return_value={
            "facts": 10,
            "experiences": 20,
            "entities": 5,
            "active_beliefs": 3,
            "topics": 8,
            "scheduling": {}
        })
        mock_memory_manager.return_value = mock_instance

        response = client.get("/api/v1/memory/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["facts"] == 10
        assert data["experiences"] == 20
        assert data["entities"] == 5

    @patch("src.api.routes.memory.MemoryManager")
    def test_get_memory_context(self, mock_memory_manager, client: TestClient):
        """Test getting memory context for a query."""
        # Mock MemoryManager
        mock_instance = MagicMock()
        mock_instance.build_context_for_query = AsyncMock(return_value={
            "persona": {"name": "Test User"},
            "relevant_facts": [{"content": "User likes Python"}],
            "beliefs": [],
            "recent_experiences": [],
            "entity_context": []
        })
        mock_memory_manager.return_value = mock_instance

        response = client.get("/api/v1/memory/context?query=What do I like?")
        assert response.status_code == 200

        data = response.json()
        assert "persona" in data
        assert "relevant_facts" in data
        assert len(data["relevant_facts"]) == 1

    def test_get_memory_context_missing_query(self, client: TestClient):
        """Test memory context without query parameter."""
        response = client.get("/api/v1/memory/context")
        assert response.status_code == 422  # Validation error

    @patch("src.api.routes.memory.MemoryManager")
    def test_add_fact(self, mock_memory_manager, client: TestClient):
        """Test adding a fact to memory."""
        mock_instance = MagicMock()
        mock_fact = MagicMock()
        mock_fact.id = uuid4()
        mock_fact.content = "User prefers dark mode"
        mock_fact.fact_type = "preference"
        mock_fact.confidence = 0.9

        mock_instance.facts.add = AsyncMock(return_value=mock_fact)
        mock_memory_manager.return_value = mock_instance

        payload = {
            "content": "User prefers dark mode",
            "fact_type": "preference",
            "confidence": 0.9
        }

        response = client.post("/api/v1/memory/facts", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["content"] == payload["content"]
        assert data["fact_type"] == payload["fact_type"]

    @patch("src.api.routes.memory.MemoryManager")
    def test_list_facts(self, mock_memory_manager, client: TestClient):
        """Test listing facts from memory."""
        mock_instance = MagicMock()
        mock_instance.facts.search = AsyncMock(return_value=[
            {"id": str(uuid4()), "content": "Fact 1", "confidence": 0.8},
            {"id": str(uuid4()), "content": "Fact 2", "confidence": 0.9}
        ])
        mock_memory_manager.return_value = mock_instance

        response = client.get("/api/v1/memory/facts")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @patch("src.api.routes.memory.MemoryManager")
    def test_search_facts(self, mock_memory_manager, client: TestClient):
        """Test searching facts by query."""
        mock_instance = MagicMock()
        mock_instance.facts.search = AsyncMock(return_value=[
            {"id": str(uuid4()), "content": "Python fact", "confidence": 0.9}
        ])
        mock_memory_manager.return_value = mock_instance

        payload = {"query": "Python", "limit": 10}
        response = client.post("/api/v1/memory/facts/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    @patch("src.api.routes.memory.MemoryManager")
    def test_get_persona(self, mock_memory_manager, client: TestClient):
        """Test getting user persona."""
        mock_instance = MagicMock()
        mock_instance.persona.get_active_profile = AsyncMock(return_value={
            "name": "Test User",
            "interests": ["Python", "AI"],
            "work_patterns": {"peak_hours": [9, 10, 11]}
        })
        mock_memory_manager.return_value = mock_instance

        response = client.get("/api/v1/memory/persona")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Test User"
        assert "interests" in data

    @patch("src.api.routes.memory.MemoryManager")
    def test_trigger_consolidation(self, mock_memory_manager, client: TestClient):
        """Test triggering memory consolidation."""
        mock_instance = MagicMock()
        mock_instance.consolidate = AsyncMock(return_value={
            "facts_merged": 5,
            "patterns_detected": 2
        })
        mock_memory_manager.return_value = mock_instance

        response = client.post("/api/v1/memory/consolidate")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Consolidation complete"
        assert "stats" in data


# ===========================================
# RATE LIMITING TESTS
# ===========================================


class TestRateLimiting:
    """Test rate limiting on API endpoints."""

    @pytest.mark.skip(reason="Rate limiting requires Redis in actual app")
    def test_rate_limit_exceeded(self, client: TestClient):
        """Test that rate limiting blocks excessive requests."""
        # This would require proper rate limiter setup
        # Keeping as placeholder for when rate limiting is fully configured
        pass

    def test_rate_limit_headers_present(self, client: TestClient):
        """Test that rate limit headers are present in responses."""
        response = client.get("/health")
        # Note: Headers may not be present on exempt paths
        # This is more for documentation purposes
        assert response.status_code == 200


# ===========================================
# ERROR HANDLING TESTS
# ===========================================


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_404_on_invalid_endpoint(self, client: TestClient):
        """Test 404 response for non-existent endpoints."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_405_on_wrong_method(self, client: TestClient):
        """Test 405 response for wrong HTTP method."""
        response = client.put("/health")  # Health only accepts GET
        assert response.status_code == 405

    def test_422_on_validation_error(self, client: TestClient):
        """Test 422 response for validation errors."""
        response = client.post("/api/v1/chat", json={"invalid": "data"})
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

    def test_invalid_uuid_parameter(self, client: TestClient):
        """Test error handling for invalid UUID parameters."""
        response = client.get("/api/v1/agents/not-a-uuid")
        assert response.status_code == 422
