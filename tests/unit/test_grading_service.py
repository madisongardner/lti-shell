"""Unit tests for grading_service.py."""
import io
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.grading_service import (
    _build_tests_tar_bytes,
    _extract_score,
    run_grading_for_attempt,
)


class TestExtractScore:
    """Tests U1-U5: score extraction logic."""

    def test_explicit_score_from_stdout(self):
        """U1: Parse 'SCORE=85' from stdout."""
        score = _extract_score("SCORE=85", "", 100.0, True)
        assert score == 85.0

    def test_decimal_score(self):
        """U2: Parse 'SCORE = 7.5' correctly."""
        score = _extract_score("SCORE = 7.5", "", 10.0, True)
        assert score == 7.5

    def test_score_clamped_to_max(self):
        """U3: Score exceeding max_points is clamped."""
        score = _extract_score("SCORE=150", "", 100.0, True)
        assert score == 100.0

    def test_score_clamped_to_zero(self):
        """U3b: Negative score is clamped to zero."""
        score = _extract_score("SCORE=-5", "", 100.0, True)
        assert score == 0.0

    def test_default_full_marks_on_pass(self):
        """U4: No SCORE token and passed gives full marks."""
        score = _extract_score("All tests passed", "", 100.0, True)
        assert score == 100.0

    def test_default_zero_on_fail(self):
        """U5: No SCORE token and failed gives zero."""
        score = _extract_score("Tests failed", "", 100.0, False)
        assert score == 0.0


class TestRunGrading:
    """Tests U6-U8: grading execution edge cases."""

    def test_timeout_status(self):
        """U6: Exit code 124 maps to 'timeout' status."""
        mock_assignment = MagicMock()
        mock_assignment.tests_extracted_path = "/fake/tests"
        mock_assignment.max_points = 100.0

        mock_attempt = MagicMock()
        mock_attempt.container_id = "abc123"

        mock_container = MagicMock()
        mock_container.id = "abc123"
        exec_result = MagicMock()
        exec_result.exit_code = 124
        exec_result.output = (b"", b"")
        mock_container.exec_run.return_value = exec_result

        with patch("services.grading_service._docker_client") as mock_dc, \
             patch("services.grading_service._build_tests_tar_bytes") as mock_tar, \
             patch("services.grading_service._stage_tests_in_container"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_dir", return_value=True):
            mock_dc.return_value.containers.get.return_value = mock_container
            mock_tar.return_value = b"fake_tar"
            result = run_grading_for_attempt(mock_assignment, mock_attempt)

        assert result["status"] == "timeout"
        assert result["exit_code"] == 124

    def test_missing_container_id(self):
        """U7: Raises ValueError when container_id is None."""
        mock_attempt = MagicMock()
        mock_attempt.container_id = None
        with pytest.raises(ValueError, match="no active container"):
            run_grading_for_attempt(MagicMock(), mock_attempt)

    def test_missing_tests_path(self):
        """U8: Raises ValueError when tests are not configured."""
        mock_attempt = MagicMock()
        mock_attempt.container_id = "abc123"
        mock_assignment = MagicMock()
        mock_assignment.tests_extracted_path = None
        with pytest.raises(ValueError, match="not configured"):
            run_grading_for_attempt(mock_assignment, mock_attempt)


class TestBuildTestsTar:
    """Test U9: tar archive construction."""

    def test_tar_has_lti_tests_prefix(self, tmp_path):
        """U9: Tar entries are prefixed with lti_tests/."""
        test_file = tmp_path / "run_tests.sh"
        test_file.write_text("#!/bin/bash\necho SCORE=100")

        tar_bytes = _build_tests_tar_bytes(tmp_path)
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r") as tf:
            names = tf.getnames()
            assert any("lti_tests/run_tests.sh" in n for n in names)
