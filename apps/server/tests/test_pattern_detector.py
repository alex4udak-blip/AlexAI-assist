"""Tests for Pattern Detection Service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.db.models import Event, Pattern
from src.services.pattern_detector import PatternDetectorService


class TestPatternDetection:
    """Test cases for pattern detection from events."""

    @pytest.mark.asyncio
    async def test_detect_app_sequences_basic(self):
        """Test detection of basic app usage sequences."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        # Create events with repeating app sequence
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_focus",
                timestamp=now - timedelta(minutes=i * 10),
                app_name=app,
                created_at=now,
            )
            for i, app in enumerate(
                ["Chrome", "VSCode", "Terminal"] * 5  # Repeat sequence 5 times
            )
        ]

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        # Detect patterns
        result = await service.detect_patterns(device_id="test-device", min_occurrences=3)

        # Verify app sequences detected
        app_sequences = result["app_sequences"]
        assert len(app_sequences) > 0
        assert any(seq["sequence"] == ["Chrome", "VSCode", "Terminal"] for seq in app_sequences)
        assert all(seq["occurrences"] >= 3 for seq in app_sequences)

    @pytest.mark.asyncio
    async def test_detect_app_sequences_automatable_flag(self):
        """Test that automatable flag is set correctly for sequences."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Create sequence with different apps (automatable)
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_focus",
                timestamp=now - timedelta(minutes=i),
                app_name=app,
                created_at=now,
            )
            for i, app in enumerate(["Chrome", "VSCode", "Terminal"] * 5)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device", min_occurrences=3)

        # Sequences with different apps should be automatable
        app_sequences = result["app_sequences"]
        assert any(seq["automatable"] is True for seq in app_sequences)

    @pytest.mark.asyncio
    async def test_detect_app_sequences_not_automatable(self):
        """Test that sequences with same app are not marked automatable."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Create sequence with same app repeated (not automatable)
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_focus",
                timestamp=now - timedelta(minutes=i),
                app_name="Chrome",
                created_at=now,
            )
            for i in range(10)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device", min_occurrences=3)

        # Sequences with same app should not be automatable
        app_sequences = result["app_sequences"]
        if app_sequences:
            same_app_sequences = [seq for seq in app_sequences if len(set(seq["sequence"])) == 1]
            assert all(seq["automatable"] is False for seq in same_app_sequences)

    @pytest.mark.asyncio
    async def test_detect_time_patterns_basic(self):
        """Test detection of time-based patterns."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        # Create events at specific hour (9 AM)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        base_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_focus",
                timestamp=base_time - timedelta(days=i),
                app_name="Slack",
                created_at=now,
            )
            for i in range(5)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device", min_occurrences=3)

        # Verify time patterns detected
        time_patterns = result["time_patterns"]
        assert len(time_patterns) > 0
        slack_patterns = [p for p in time_patterns if p["app"] == "Slack"]
        assert len(slack_patterns) > 0
        assert slack_patterns[0]["hour"] == 9
        assert slack_patterns[0]["occurrences"] >= 3
        assert slack_patterns[0]["automatable"] is True

    @pytest.mark.asyncio
    async def test_detect_context_switches_high(self):
        """Test detection of high context switching behavior."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        # Create events with frequent app switches
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        apps = ["Chrome", "VSCode", "Slack", "Terminal", "Chrome", "Slack"]
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_focus",
                timestamp=now - timedelta(minutes=i),
                app_name=app,
                created_at=now,
            )
            for i, app in enumerate(apps)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device")

        # Verify context switches detected
        context_switches = result["context_switches"]
        assert context_switches["total_switches"] > 0
        assert 0 <= context_switches["switch_rate"] <= 1
        assert context_switches["assessment"] in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_detect_context_switches_low(self):
        """Test detection of low context switching behavior."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        # Create events with same app (no switches)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_focus",
                timestamp=now - timedelta(minutes=i),
                app_name="VSCode",
                created_at=now,
            )
            for i in range(10)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device")

        # Verify low switching rate
        context_switches = result["context_switches"]
        assert context_switches["switch_rate"] < 0.3
        assert context_switches["assessment"] == "low"


class TestPatternScoring:
    """Test cases for pattern scoring and ranking."""

    @pytest.mark.asyncio
    async def test_pattern_occurrences_counting(self):
        """Test that pattern occurrences are counted correctly."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Create sequence that repeats exactly 7 times
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_focus",
                timestamp=now - timedelta(minutes=i),
                app_name=app,
                created_at=now,
            )
            for i, app in enumerate(["App1", "App2", "App3"] * 7)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device", min_occurrences=3)

        # Find the specific sequence
        app_sequences = result["app_sequences"]
        target_seq = next((s for s in app_sequences if s["sequence"] == ["App1", "App2", "App3"]), None)
        assert target_seq is not None
        assert target_seq["occurrences"] >= 5  # Should detect multiple occurrences

    @pytest.mark.asyncio
    async def test_patterns_sorted_by_occurrences(self):
        """Test that patterns are sorted by occurrence count."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Create multiple sequences with different frequencies
        events = []
        # High frequency sequence
        for _ in range(15):
            events.extend([
                Event(
                    id=uuid4(),
                    device_id="test-device",
                    event_type="app_focus",
                    timestamp=now - timedelta(minutes=len(events) + j),
                    app_name=app,
                    created_at=now,
                )
                for j, app in enumerate(["High1", "High2", "High3"])
            ])
        # Low frequency sequence
        for _ in range(3):
            events.extend([
                Event(
                    id=uuid4(),
                    device_id="test-device",
                    event_type="app_focus",
                    timestamp=now - timedelta(minutes=len(events) + j),
                    app_name=app,
                    created_at=now,
                )
                for j, app in enumerate(["Low1", "Low2", "Low3"])
            ])

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device", min_occurrences=3)

        # Verify patterns are sorted by occurrences (descending)
        app_sequences = result["app_sequences"]
        if len(app_sequences) > 1:
            for i in range(len(app_sequences) - 1):
                assert app_sequences[i]["occurrences"] >= app_sequences[i + 1]["occurrences"]

    @pytest.mark.asyncio
    async def test_min_occurrences_filter(self):
        """Test that patterns below min_occurrences are filtered out."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Create sequence that repeats only 2 times
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_focus",
                timestamp=now - timedelta(minutes=i),
                app_name=app,
                created_at=now,
            )
            for i, app in enumerate(["Rare1", "Rare2", "Rare3"] * 2)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device", min_occurrences=5)

        # Pattern with only 2 occurrences should not appear
        app_sequences = result["app_sequences"]
        assert not any(s["sequence"] == ["Rare1", "Rare2", "Rare3"] for s in app_sequences)

    @pytest.mark.asyncio
    async def test_top_10_patterns_limit(self):
        """Test that only top 10 patterns are returned."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Create many different sequences
        events = []
        for seq_num in range(20):
            for _ in range(5):  # Each sequence repeats 5 times
                events.extend([
                    Event(
                        id=uuid4(),
                        device_id="test-device",
                        event_type="app_focus",
                        timestamp=now - timedelta(minutes=len(events) + j),
                        app_name=f"App{seq_num}_{j}",
                        created_at=now,
                    )
                    for j in range(3)
                ])

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device", min_occurrences=3)

        # Should return at most 10 patterns
        app_sequences = result["app_sequences"]
        assert len(app_sequences) <= 10


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_no_events(self):
        """Test pattern detection with no events."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device")

        # Should return empty patterns
        assert result["app_sequences"] == []
        assert result["time_patterns"] == []
        assert result["context_switches"]["total_switches"] == 0
        assert result["context_switches"]["switch_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_single_event(self):
        """Test pattern detection with only one event."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_focus",
                timestamp=now,
                app_name="Chrome",
                created_at=now,
            )
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device")

        # Single event should not create patterns
        assert result["app_sequences"] == []
        assert result["context_switches"]["total_switches"] == 0

    @pytest.mark.asyncio
    async def test_events_with_no_app_name(self):
        """Test handling of events without app_name."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="system_event",
                timestamp=now - timedelta(minutes=i),
                app_name=None,
                created_at=now,
            )
            for i in range(10)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device")

        # Events without app_name should be filtered out
        assert result["app_sequences"] == []
        assert result["time_patterns"] == []

    @pytest.mark.asyncio
    async def test_duplicate_events(self):
        """Test handling of duplicate events."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Create duplicate events (same app at same time)
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_focus",
                timestamp=now,
                app_name="Chrome",
                created_at=now,
            )
            for _ in range(5)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device")

        # Should handle duplicates without crashing
        assert result is not None
        assert "app_sequences" in result
        assert "context_switches" in result

    @pytest.mark.asyncio
    async def test_mixed_app_names_and_none(self):
        """Test events with mix of valid app names and None."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        apps = ["Chrome", None, "VSCode", None, "Terminal", "Chrome", "VSCode", "Terminal"]
        events = [
            Event(
                id=uuid4(),
                device_id="test-device",
                event_type="app_focus",
                timestamp=now - timedelta(minutes=i),
                app_name=app,
                created_at=now,
            )
            for i, app in enumerate(apps)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        result = await service.detect_patterns(device_id="test-device")

        # Should filter None values and still detect patterns
        assert result is not None
        app_sequences = result["app_sequences"]
        # Verify no None in detected sequences
        for seq in app_sequences:
            assert None not in seq["sequence"]

    @pytest.mark.asyncio
    async def test_device_id_filter(self):
        """Test that device_id filter is applied correctly."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = [
            Event(
                id=uuid4(),
                device_id="device-1",
                event_type="app_focus",
                timestamp=now - timedelta(minutes=i),
                app_name="Chrome",
                created_at=now,
            )
            for i in range(5)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        # Detect patterns with specific device_id
        await service.detect_patterns(device_id="device-1")

        # Verify query was executed (device filter applied)
        assert db_mock.execute.called

    @pytest.mark.asyncio
    async def test_no_device_id_filter(self):
        """Test pattern detection across all devices."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        events = [
            Event(
                id=uuid4(),
                device_id=f"device-{i % 3}",
                event_type="app_focus",
                timestamp=now - timedelta(minutes=i),
                app_name="Chrome",
                created_at=now,
            )
            for i in range(10)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        db_mock.execute = AsyncMock(return_value=mock_result)

        # Detect patterns without device_id filter
        result = await service.detect_patterns(device_id=None)

        # Should work across all devices
        assert result is not None
        assert "app_sequences" in result


class TestPatternPersistence:
    """Test cases for saving and retrieving patterns."""

    @pytest.mark.asyncio
    async def test_save_pattern(self):
        """Test saving a detected pattern to database."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        pattern = await service.save_pattern(
            name="Morning Routine",
            pattern_type="app_sequence",
            trigger_conditions={"time": "09:00"},
            sequence=[{"app": "Chrome"}, {"app": "Slack"}],
            occurrences=10,
            automatable=True,
        )

        # Verify pattern was created with correct attributes
        assert pattern.name == "Morning Routine"
        assert pattern.pattern_type == "app_sequence"
        assert pattern.occurrences == 10
        assert pattern.automatable is True
        assert pattern.first_seen_at is not None
        assert pattern.last_seen_at is not None

        # Verify pattern was added to session
        db_mock.add.assert_called_once()
        db_mock.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_patterns_all(self):
        """Test retrieving all patterns."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        # Mock database response
        mock_patterns = [
            Pattern(
                id=uuid4(),
                name="Pattern 1",
                pattern_type="app_sequence",
                trigger_conditions={},
                sequence=[],
                occurrences=5,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            ),
            Pattern(
                id=uuid4(),
                name="Pattern 2",
                pattern_type="time_based",
                trigger_conditions={},
                sequence=[],
                occurrences=3,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            ),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_patterns
        db_mock.execute = AsyncMock(return_value=mock_result)

        patterns = await service.get_patterns()

        # Verify patterns retrieved
        assert len(patterns) == 2
        assert patterns[0].name == "Pattern 1"
        assert patterns[1].name == "Pattern 2"

    @pytest.mark.asyncio
    async def test_get_patterns_with_status_filter(self):
        """Test retrieving patterns filtered by status."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_mock.execute = AsyncMock(return_value=mock_result)

        await service.get_patterns(status="active")

        # Verify execute was called (status filter applied)
        assert db_mock.execute.called

    @pytest.mark.asyncio
    async def test_get_patterns_with_automatable_filter(self):
        """Test retrieving patterns filtered by automatable flag."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_mock.execute = AsyncMock(return_value=mock_result)

        await service.get_patterns(automatable=True)

        # Verify execute was called (automatable filter applied)
        assert db_mock.execute.called

    @pytest.mark.asyncio
    async def test_get_patterns_with_limit(self):
        """Test retrieving patterns with custom limit."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_mock.execute = AsyncMock(return_value=mock_result)

        await service.get_patterns(limit=10)

        # Verify execute was called with limit
        assert db_mock.execute.called

    @pytest.mark.asyncio
    async def test_get_pattern_by_id(self):
        """Test retrieving a specific pattern by ID."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        pattern_id = uuid4()
        mock_pattern = Pattern(
            id=pattern_id,
            name="Test Pattern",
            pattern_type="app_sequence",
            trigger_conditions={},
            sequence=[],
            occurrences=5,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pattern
        db_mock.execute = AsyncMock(return_value=mock_result)

        pattern = await service.get_pattern(pattern_id)

        # Verify correct pattern retrieved
        assert pattern is not None
        assert pattern.id == pattern_id
        assert pattern.name == "Test Pattern"

    @pytest.mark.asyncio
    async def test_get_pattern_not_found(self):
        """Test retrieving a non-existent pattern."""
        db_mock = AsyncMock()
        service = PatternDetectorService(db_mock)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_mock.execute = AsyncMock(return_value=mock_result)

        pattern = await service.get_pattern(uuid4())

        # Should return None for non-existent pattern
        assert pattern is None
