"""Unit tests for docker_service.py."""
from unittest.mock import MagicMock, patch

import pytest
from docker.errors import NotFound

from services.docker_service import (
    _user_ids,
    create_attempt_container,
    terminate_attempt_container,
    populate_workspace_from_starter,
)


class TestUserIds:
    """Tests U10-U12: UID/GID parsing."""

    def test_uid_gid_pair(self):
        """U10: Standard uid:gid string."""
        assert _user_ids("65532:65532") == (65532, 65532)

    def test_uid_only(self):
        """U11: UID only defaults GID to same value."""
        assert _user_ids("1000") == (1000, 1000)

    def test_invalid_returns_default(self):
        """U12: Non-numeric input returns defaults."""
        assert _user_ids("abc") == (65532, 65532)


class TestCreateContainer:
    """Test U13: Container creation parameters."""

    @patch("services.docker_service._client")
    def test_security_flags(self, mock_client_fn):
        """U13: Verify container runs with security hardening."""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "test123"
        mock_container.status = "running"
        mock_client.containers.run.return_value = mock_container
        mock_client_fn.return_value = mock_client

        result = create_attempt_container()

        call_kwargs = mock_client.containers.run.call_args[1]
        assert call_kwargs["network_disabled"] is True
        assert call_kwargs["cap_drop"] == ["ALL"]
        assert "no-new-privileges:true" in call_kwargs["security_opt"]
        assert call_kwargs["pids_limit"] == 128
        assert result["container_id"] == "test123"


class TestTerminateContainer:
    """Tests U14-U15: Container termination."""

    def test_none_container(self):
        """U14: None container_id returns False."""
        assert terminate_attempt_container(None) is False

    @patch("services.docker_service._client")
    def test_not_found_returns_false(self, mock_client_fn):
        """U15: NotFound exception returns False."""
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("gone")
        mock_client_fn.return_value = mock_client
        assert terminate_attempt_container("missing") is False


class TestPopulateWorkspace:
    """Tests U16-U17: Workspace population."""

    def test_no_starter_path(self):
        """U17: Returns copied=False when starter path is None."""
        result = populate_workspace_from_starter("abc123", None)
        assert result["copied"] is False
        assert result["file_count"] == 0
