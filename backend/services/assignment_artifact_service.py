"""Assignment artifact upload, validation, and extraction helpers."""

import os
import posixpath
import re
import shutil
import stat
import zipfile
from pathlib import Path

MAX_UPLOAD_BYTES = int(os.getenv("LTI_SHELL_ASSIGNMENT_MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
MAX_EXTRACTED_BYTES = int(os.getenv("LTI_SHELL_ASSIGNMENT_MAX_EXTRACTED_BYTES", str(20 * 1024 * 1024)))
MAX_ARCHIVE_FILES = int(os.getenv("LTI_SHELL_ASSIGNMENT_MAX_ARCHIVE_FILES", "500"))
ASSIGNMENT_STORAGE_DIR = Path(
    os.getenv(
        "LTI_SHELL_ASSIGNMENT_STORAGE_DIR",
        str(Path(__file__).resolve().parents[1] / "artifacts"),
    )
)


class ArtifactValidationError(ValueError):
    """Raised when uploaded artifact content is invalid or unsafe."""


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value or "")
    cleaned = cleaned.strip("._")
    return cleaned[:80] or "unknown"


def _assignment_root(assignment) -> Path:
    course = _slug(assignment.course_id)
    assignment_id = _slug(assignment.assignment_id)
    return ASSIGNMENT_STORAGE_DIR / f"course_{course}" / f"assignment_{assignment_id}"


def _validate_archive_name(name: str) -> str:
    if not name or "\x00" in name:
        raise ArtifactValidationError("Archive contains invalid file name")

    normalized = posixpath.normpath(name)
    if normalized.startswith("../") or normalized.startswith("/") or normalized == "..":
        raise ArtifactValidationError("Archive contains unsafe paths")

    return normalized


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_IFMT(mode) == stat.S_IFLNK


def _validate_zip_file(zip_path: Path, required_file: str | None = None) -> dict:
    if not zipfile.is_zipfile(zip_path):
        raise ArtifactValidationError("Uploaded file must be a valid ZIP archive")

    total_uncompressed = 0
    file_count = 0
    found_required = required_file is None

    with zipfile.ZipFile(zip_path, "r") as zf:
        infos = zf.infolist()
        if len(infos) > MAX_ARCHIVE_FILES:
            raise ArtifactValidationError("Archive contains too many files")

        for info in infos:
            normalized = _validate_archive_name(info.filename)
            if info.is_dir():
                continue

            if _is_symlink(info):
                raise ArtifactValidationError("Archive contains symlinks, which are not allowed")

            file_count += 1
            total_uncompressed += int(info.file_size)
            if total_uncompressed > MAX_EXTRACTED_BYTES:
                raise ArtifactValidationError("Archive exceeds extracted size limit")

            if required_file and posixpath.basename(normalized) == required_file:
                found_required = True

    if required_file and not found_required:
        raise ArtifactValidationError(f"Archive must include {required_file}")

    return {
        "file_count": file_count,
        "total_uncompressed": total_uncompressed,
        "has_required_file": found_required,
    }


def _clear_dir(path: Path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _extract_zip(zip_path: Path, dest_dir: Path):
    _clear_dir(dest_dir)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            normalized = _validate_archive_name(info.filename)
            target = dest_dir / normalized
            target_parent = target.parent
            target_parent.mkdir(parents=True, exist_ok=True)

            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            with zf.open(info, "r") as source, open(target, "wb") as output:
                shutil.copyfileobj(source, output)


def save_assignment_archive(file_storage, assignment, artifact_kind: str) -> dict:
    """Validate and store assignment artifact zip.

    artifact_kind: starter | tests
    """
    if artifact_kind not in {"starter", "tests"}:
        raise ArtifactValidationError("Unsupported artifact type")

    if not file_storage:
        raise ArtifactValidationError("No file was uploaded")

    original_name = file_storage.filename or ""
    if not original_name.lower().endswith(".zip"):
        raise ArtifactValidationError("Only .zip files are allowed")

    root = _assignment_root(assignment)
    root.mkdir(parents=True, exist_ok=True)

    upload_dir = root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    zip_path = upload_dir / f"{artifact_kind}.zip"
    file_storage.save(zip_path)

    size_bytes = zip_path.stat().st_size
    if size_bytes > MAX_UPLOAD_BYTES:
        zip_path.unlink(missing_ok=True)
        raise ArtifactValidationError("Uploaded ZIP exceeds size limit")

    required = "run_tests.sh" if artifact_kind == "tests" else None
    validation = _validate_zip_file(zip_path, required_file=required)

    extract_dir = root / artifact_kind
    _extract_zip(zip_path, extract_dir)

    return {
        "zip_path": str(zip_path),
        "extracted_path": str(extract_dir),
        "has_required_test_runner": bool(validation["has_required_file"]),
        "file_count": validation["file_count"],
        "total_uncompressed": validation["total_uncompressed"],
    }
