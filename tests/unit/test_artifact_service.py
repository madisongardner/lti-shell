"""Unit tests for assignment_artifact_service.py."""
import io
import os
import stat
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from services.assignment_artifact_service import (
    ArtifactValidationError,
    _slug,
    _validate_zip_file,
    save_assignment_archive,
)


class TestSlug:
    """Test U25: Slug sanitization."""

    def test_strips_special_chars(self):
        """U25: Special characters are replaced with underscores."""
        assert _slug("My Course! @#$") == "My_Course"

    def test_truncates_to_80(self):
        """U25b: Long strings are truncated."""
        long_name = "a" * 200
        assert len(_slug(long_name)) == 80


class TestValidateZip:
    """Tests U18-U24: ZIP validation."""

    def _make_zip(self, tmp_path, files):
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for name, content in files.items():
                zf.writestr(name, content)
        return zip_path

    def test_reject_non_zip(self, tmp_path):
        """U18: Non-zip file raises error."""
        bad_file = tmp_path / "fake.zip"
        bad_file.write_text("not a zip file")
        with pytest.raises(ArtifactValidationError, match="valid ZIP"):
            _validate_zip_file(bad_file)

    def test_reject_path_traversal(self, tmp_path):
        """U21: Entries with ../ are rejected."""
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../../etc/passwd", "pwned")
        with pytest.raises(ArtifactValidationError, match="unsafe"):
            _validate_zip_file(zip_path)

    def test_reject_too_many_files(self, tmp_path):
        """U22: Archives exceeding file count limit are rejected."""
        zip_path = tmp_path / "big.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(501):
                zf.writestr(f"file_{i}.txt", "x")
        with pytest.raises(ArtifactValidationError, match="too many"):
            _validate_zip_file(zip_path)

    def test_reject_missing_test_runner(self, tmp_path):
        """U23: Tests zip without run_tests.sh raises error."""
        zip_path = self._make_zip(tmp_path, {"helper.sh": "echo hi"})
        with pytest.raises(ArtifactValidationError, match="run_tests.sh"):
            _validate_zip_file(zip_path, required_file="run_tests.sh")

    def test_accept_valid_tests_zip(self, tmp_path):
        """U24: Valid tests zip passes validation."""
        zip_path = self._make_zip(tmp_path, {
            "run_tests.sh": "#!/bin/bash\necho SCORE=100",
            "test_helper.sh": "echo helper",
        })
        result = _validate_zip_file(zip_path, required_file="run_tests.sh")
        assert result["has_required_file"] is True
        assert result["file_count"] == 2


class TestSaveArchive:
    """Tests U18-U19: Upload validation in save flow."""

    def test_reject_non_zip_extension(self, tmp_path):
        """U18: Non-.zip filename is rejected."""
        mock_file = MagicMock()
        mock_file.filename = "archive.tar.gz"
        mock_assignment = MagicMock()
        mock_assignment.course_id = "CS101"
        mock_assignment.assignment_id = "a1"
        with pytest.raises(ArtifactValidationError, match=".zip"):
            save_assignment_archive(mock_file, mock_assignment, "starter")
