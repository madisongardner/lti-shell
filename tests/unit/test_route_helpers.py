"""Unit tests for route authorization helpers."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from flask import Flask

from routes.assignments import (
    _can_access_attempt,
    _parse_due_at,
    _coerce_max_points,
    _serialize_datetime,
    _validate_assignment_payload,
)


class TestCanAccessAttempt:
    """Tests U37: Cross-resource access control."""

    def test_student_same_resource(self):
        """U37a: Student can access own attempt."""
        user = {"sub": "user1", "resource_link_id": "rl1", "role": "student"}
        attempt = type("A", (), {"user_sub": "user1", "resource_link_id": "rl1"})()
        assert _can_access_attempt(user, attempt) is True

    def test_student_wrong_resource(self):
        """U37b: Student cannot access another resource's attempt."""
        user = {"sub": "user1", "resource_link_id": "rl1", "role": "student"}
        attempt = type("A", (), {"user_sub": "user1", "resource_link_id": "rl2"})()
        assert _can_access_attempt(user, attempt) is False

    def test_teacher_same_resource(self):
        """U37c: Teacher can access attempts within their resource."""
        user = {"sub": "teacher1", "resource_link_id": "rl1", "role": "teacher"}
        attempt = type("A", (), {"user_sub": "user1", "resource_link_id": "rl1"})()
        assert _can_access_attempt(user, attempt) is True


class TestParseDueAt:
    """Test U39: Due date parsing."""

    def test_iso_with_timezone(self):
        """U39a: ISO string with timezone."""
        result = _parse_due_at("2026-05-01T23:59:00+00:00")
        assert result.year == 2026
        assert result.tzinfo is not None

    def test_iso_with_z(self):
        """U39b: ISO string with Z suffix."""
        result = _parse_due_at("2026-05-01T23:59:00Z")
        assert result.tzinfo is not None

    def test_none_returns_none(self):
        """U39c: None input returns None."""
        assert _parse_due_at(None) is None


class TestSerializeDatetime:
    """Datetime serialization for API payloads."""

    def test_naive_datetime_is_serialized_as_utc(self):
        """Naive datetimes should not round-trip as local browser time."""
        result = _serialize_datetime(datetime(2026, 5, 2, 1, 0, 0))
        assert result == "2026-05-02T01:00:00Z"

    def test_aware_datetime_is_normalized_to_utc(self):
        """Aware datetimes should be serialized with explicit UTC."""
        result = _serialize_datetime(
            datetime(2026, 5, 2, 1, 0, 0, tzinfo=timezone.utc),
        )
        assert result == "2026-05-02T01:00:00Z"


class TestCoerceMaxPoints:
    """Test U40: Max points validation."""

    def test_negative_raises(self):
        """U40a: Negative value raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            _coerce_max_points(-5)

    def test_zero_raises(self):
        """U40b: Zero raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            _coerce_max_points(0)

    def test_valid_float(self):
        """U40c: Valid numeric string is coerced."""
        assert _coerce_max_points("100") == 100.0


class TestValidatePayload:
    """Test U38: Assignment payload validation."""

    def test_empty_title_rejected(self):
        """U38: Empty title raises ValueError."""
        with pytest.raises(ValueError, match="title"):
            _validate_assignment_payload({"title": "", "instructions": "Do stuff", "max_points": 100})
