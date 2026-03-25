"""Submission grading helpers."""

import io
import os
import re
import tarfile
from pathlib import Path

import docker
from docker.errors import DockerException, NotFound

DEFAULT_GRADING_TIMEOUT_SECONDS = int(os.getenv("LTI_SHELL_GRADING_TIMEOUT_SECONDS", "30"))
SCORE_PATTERN = re.compile(r"SCORE\s*=\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)


def _docker_client():
	try:
		client = docker.from_env()
		client.ping()
		return client
	except DockerException as exc:
		raise RuntimeError(f"Docker unavailable for grading: {exc}") from exc


def _build_tests_tar_bytes(tests_dir: Path) -> bytes:
	if not tests_dir.exists() or not tests_dir.is_dir():
		raise ValueError("Tests artifact directory is missing")

	buff = io.BytesIO()
	with tarfile.open(fileobj=buff, mode="w") as tar:
		for file_path in tests_dir.rglob("*"):
			rel_path = file_path.relative_to(tests_dir)
			arcname = Path("lti_tests") / rel_path
			tar.add(file_path, arcname=str(arcname))
	buff.seek(0)
	return buff.getvalue()


def _decode_output(raw):
	if raw is None:
		return ""
	if isinstance(raw, bytes):
		return raw.decode("utf-8", "replace")
	return str(raw)


def _extract_score(stdout: str, stderr: str, max_points: float, passed: bool) -> float:
	combined = "\n".join([stdout or "", stderr or ""])
	match = SCORE_PATTERN.search(combined)
	if match:
		score = float(match.group(1))
		return max(0.0, min(score, float(max_points)))
	return float(max_points) if passed else 0.0


def run_grading_for_attempt(assignment, attempt):
	"""Execute assignment tests against the current attempt container."""
	if not attempt.container_id:
		raise ValueError("Attempt has no active container")

	if not assignment.tests_extracted_path:
		raise ValueError("Assignment tests are not configured")

	timeout_seconds = DEFAULT_GRADING_TIMEOUT_SECONDS
	tests_dir = Path(assignment.tests_extracted_path)

	client = _docker_client()
	try:
		container = client.containers.get(attempt.container_id)
	except NotFound as exc:
		raise ValueError("Attempt container not found") from exc

	tests_tar = _build_tests_tar_bytes(tests_dir)
	copied = container.put_archive("/tmp", tests_tar)
	if not copied:
		raise RuntimeError("Unable to stage tests in container")

	run_cmd = (
		"set -e; "
		"cd /tmp/lti_tests; "
		"RUNNER=$(find . -type f -name run_tests.sh | head -n1); "
		"if [ -z \"$RUNNER\" ]; then echo 'Missing run_tests.sh' >&2; exit 2; fi; "
		"chmod +x \"$RUNNER\"; "
		"cd /workspace; "
		f"timeout {timeout_seconds}s bash \"/tmp/lti_tests/${{RUNNER#./}}\""
	)

	result = container.exec_run(
		["/bin/bash", "-lc", run_cmd],
		demux=True,
		stdout=True,
		stderr=True,
		tty=False,
	)
	stdout_bytes, stderr_bytes = result.output if result.output else (b"", b"")
	stdout = _decode_output(stdout_bytes)
	stderr = _decode_output(stderr_bytes)

	exit_code = int(result.exit_code)
	if exit_code == 124:
		status = "timeout"
	elif exit_code == 0:
		status = "passed"
	else:
		status = "failed"

	score = _extract_score(stdout, stderr, assignment.max_points, passed=(status == "passed"))
	return {
		"status": status,
		"score": score,
		"stdout": stdout,
		"stderr": stderr,
		"exit_code": exit_code,
	}
