from contextlib import contextmanager
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database import SessionLocal
from models.assignment import Assignment
from models.attempt import Attempt
from models.submission import Submission
from services.docker_service import (
    create_attempt_container,
    get_container_status,
    populate_workspace_from_starter,
    reset_attempt_container,
    terminate_attempt_container,
)
from services.attempt_cleanup_service import refresh_attempt_timeout
from services.assignment_artifact_service import (
    ArtifactValidationError,
    clear_assignment_archive,
    save_assignment_archive,
)
from services.audit_service import log_event
from services.grading_service import run_grading_for_attempt
from services.lti_ags_service import post_grade_with_retry

assignments_bp = Blueprint("assignments", __name__)


@contextmanager
def _db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _require_user():
    user = session.get("user")
    if not user:
        return None, (jsonify({"error": "Not authenticated"}), 401)
    if not user.get("sub") or not user.get("resource_link_id"):
        return None, (jsonify({"error": "Missing launch context in session"}), 400)
    return user, None


def _can_access_attempt(user, attempt):
    if user.get("role") == "teacher":
        return attempt.resource_link_id == user.get("resource_link_id")
    return (
        attempt.user_sub == user.get("sub")
        and attempt.resource_link_id == user.get("resource_link_id")
    )


def _require_teacher():
    user, error_response = _require_user()
    if error_response:
        return None, error_response
    if user.get("role") != "teacher":
        return None, (jsonify({"error": "Teacher access required"}), 403)
    if not user.get("course_id"):
        return None, (jsonify({"error": "Missing course context in session"}), 400)
    return user, None


def _require_student():
    user, error_response = _require_user()
    if error_response:
        return None, error_response
    if user.get("role") == "teacher":
        return None, (jsonify({"error": "Student access required"}), 403)
    return user, None


def _serialize_assignment(assignment):
    reasons = _get_assignment_configuration_reasons(assignment)
    return {
        "assignment_id": assignment.assignment_id,
        "instructor_sub": assignment.instructor_sub,
        "course_id": assignment.course_id,
        "resource_link_id": assignment.resource_link_id,
        "lineitem_url": assignment.lineitem_url,
        "title": assignment.title,
        "instructions": assignment.instructions,
        "due_at": _serialize_datetime(assignment.due_at),
        "max_points": assignment.max_points,
        "is_configured": assignment.is_configured,
        "starter_zip_uploaded": bool(assignment.starter_zip_path),
        "tests_zip_uploaded": bool(assignment.tests_zip_path),
        "has_required_test_runner": bool(assignment.has_required_test_runner),
        "artifacts_validated": bool(assignment.artifacts_validated),
        "artifact_validation_error": assignment.artifact_validation_error,
        "configuration_reasons": reasons,
        "created_at": _serialize_datetime(assignment.created_at),
        "updated_at": _serialize_datetime(assignment.updated_at),
    }


def _serialize_submission(submission):
    return {
        "submission_id": submission.submission_id,
        "assignment_id": submission.assignment_id,
        "attempt_id": submission.attempt_id,
        "user_sub": submission.user_sub,
        "resource_link_id": submission.resource_link_id,
        "status": submission.status,
        "score": submission.score,
        "max_points": submission.max_points,
        "feedback_stdout": submission.feedback_stdout,
        "feedback_stderr": submission.feedback_stderr,
        "passback_status": submission.passback_status,
        "passback_attempts": submission.passback_attempts,
        "passback_last_error": submission.passback_last_error,
        "passback_completed_at": _serialize_datetime(submission.passback_completed_at),
        "created_at": _serialize_datetime(submission.created_at),
        "completed_at": _serialize_datetime(submission.completed_at),
    }


def _can_access_submission(user, submission):
    if user.get("role") == "teacher":
        return submission.resource_link_id == user.get("resource_link_id")
    return submission.user_sub == user.get("sub") and submission.resource_link_id == user.get("resource_link_id")


def _get_assignment_configuration_reasons(assignment):
    reasons = []
    if not assignment.title or not assignment.title.strip():
        reasons.append("Missing assignment title")
    if not assignment.instructions or not assignment.instructions.strip():
        reasons.append("Missing assignment instructions")
    if assignment.max_points is None or assignment.max_points <= 0:
        reasons.append("Max points must be positive")
    if not assignment.starter_zip_path:
        reasons.append("Starter ZIP not uploaded")
    if not assignment.tests_zip_path:
        reasons.append("Tests ZIP not uploaded")
    if not assignment.has_required_test_runner:
        reasons.append("Tests ZIP must include run_tests.sh")
    if not assignment.artifacts_validated:
        reasons.append("Artifacts have not passed validation")
    if assignment.artifact_validation_error:
        reasons.append(assignment.artifact_validation_error)

    deduped = []
    seen = set()
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            deduped.append(reason)
    return deduped


def _serialize_datetime(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _refresh_assignment_configuration(assignment):
    assignment.is_configured = len(_get_assignment_configuration_reasons(assignment)) == 0


def _get_assignment_owned_by_teacher(db, user, assignment_id):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        return None, (jsonify({"error": "Assignment not found"}), 404)
    if assignment.course_id != user.get("course_id"):
        return None, (jsonify({"error": "Forbidden"}), 403)
    return assignment, None


def _parse_due_at(value):
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("due_at must be an ISO 8601 datetime string")

    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _coerce_max_points(value):
    try:
        points = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_points must be a positive number") from exc

    if points <= 0:
        raise ValueError("max_points must be a positive number")
    return points


def _validate_assignment_payload(payload):
    title = (payload.get("title") or "").strip()
    instructions = (payload.get("instructions") or "").strip()
    if not title:
        raise ValueError("title is required")
    if not instructions:
        raise ValueError("instructions is required")

    due_at = _parse_due_at(payload.get("due_at"))
    max_points = _coerce_max_points(payload.get("max_points", 100))

    return {
        "title": title,
        "instructions": instructions,
        "due_at": due_at,
        "max_points": max_points,
    }


def _get_assignment_for_launch(db, user):
    return (
        db.query(Assignment)
        .filter(Assignment.course_id == user.get("course_id", ""))
        .filter(Assignment.resource_link_id == user.get("resource_link_id", ""))
        .order_by(Assignment.is_configured.desc(), Assignment.updated_at.desc())
        .first()
    )


@assignments_bp.route("/assignments", methods=["POST"])
def create_assignment():
    user, error_response = _require_teacher()
    if error_response:
        return error_response

    payload = request.get_json(silent=True) or {}
    try:
        validated = _validate_assignment_payload(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    resource_link_id = (payload.get("resource_link_id") or user.get("resource_link_id") or "").strip()
    if not resource_link_id:
        return jsonify({"error": "resource_link_id is required"}), 400

    with _db_session() as db:
        existing = (
            db.query(Assignment)
            .filter(Assignment.course_id == user.get("course_id", ""))
            .filter(Assignment.resource_link_id == resource_link_id)
            .first()
        )
        if existing:
            return jsonify({"error": "An assignment already exists for this activity link"}), 409

        assignment = Assignment(
            instructor_sub=user.get("sub", ""),
            course_id=user.get("course_id", ""),
            resource_link_id=resource_link_id,
            lineitem_url=(payload.get("lineitem_url") or user.get("lineitem_url") or "").strip(),
            title=validated["title"],
            instructions=validated["instructions"],
            due_at=validated["due_at"],
            max_points=validated["max_points"],
        )
        _refresh_assignment_configuration(assignment)
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        log_event(
            "assignment.created",
            actor_sub=user.get("sub", ""),
            resource_link_id=assignment.resource_link_id,
            details={
                "assignment_id": assignment.assignment_id,
                "course_id": assignment.course_id,
                "title": assignment.title,
            },
        )
        return jsonify(_serialize_assignment(assignment)), 201


@assignments_bp.route("/assignments", methods=["GET"])
def list_assignments():
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        query = db.query(Assignment)
        if user.get("role") == "teacher":
            query = query.filter(Assignment.course_id == user.get("course_id", ""))
        else:
            query = query.filter(Assignment.course_id == user.get("course_id", ""))
            query = query.filter(Assignment.resource_link_id == user.get("resource_link_id", ""))

        assignments = query.order_by(Assignment.created_at.desc()).all()
        return jsonify({"items": [_serialize_assignment(item) for item in assignments]})


@assignments_bp.route("/assignments/current", methods=["GET"])
def get_current_assignment():
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        assignment = _get_assignment_for_launch(db, user)
        if not assignment:
            return jsonify({"error": "No assignment configured for this activity"}), 404
        return jsonify(_serialize_assignment(assignment))


@assignments_bp.route("/assignments/<assignment_id>", methods=["PATCH"])
def update_assignment(assignment_id):
    user, error_response = _require_teacher()
    if error_response:
        return error_response

    payload = request.get_json(silent=True) or {}
    with _db_session() as db:
        assignment, lookup_error = _get_assignment_owned_by_teacher(db, user, assignment_id)
        if lookup_error:
            return lookup_error

        try:
            if "title" in payload:
                title = (payload.get("title") or "").strip()
                if not title:
                    raise ValueError("title is required")
                assignment.title = title

            if "instructions" in payload:
                instructions = (payload.get("instructions") or "").strip()
                if not instructions:
                    raise ValueError("instructions is required")
                assignment.instructions = instructions

            if "due_at" in payload:
                assignment.due_at = _parse_due_at(payload.get("due_at"))

            if "max_points" in payload:
                assignment.max_points = _coerce_max_points(payload.get("max_points"))

            if "lineitem_url" in payload:
                assignment.lineitem_url = (payload.get("lineitem_url") or "").strip()

            _refresh_assignment_configuration(assignment)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        db.commit()
        db.refresh(assignment)
        log_event(
            "assignment.updated",
            actor_sub=user.get("sub", ""),
            resource_link_id=assignment.resource_link_id,
            details={"assignment_id": assignment.assignment_id},
        )
        return jsonify(_serialize_assignment(assignment))


@assignments_bp.route("/assignments/<assignment_id>/attach-current-activity", methods=["POST"])
def attach_assignment_to_current_activity(assignment_id):
    user, error_response = _require_teacher()
    if error_response:
        return error_response

    current_resource_link_id = (user.get("resource_link_id") or "").strip()
    if not current_resource_link_id:
        return jsonify({"error": "Missing resource link context in session"}), 400

    with _db_session() as db:
        assignment, lookup_error = _get_assignment_owned_by_teacher(db, user, assignment_id)
        if lookup_error:
            return lookup_error

        existing_for_activity = (
            db.query(Assignment)
            .filter(Assignment.course_id == user.get("course_id", ""))
            .filter(Assignment.resource_link_id == current_resource_link_id)
            .filter(Assignment.assignment_id != assignment.assignment_id)
            .all()
        )

        replaced_assignment_ids = []
        for attached in existing_for_activity:
            # Detach any currently attached assignment from this activity.
            attached.resource_link_id = ""
            attached.lineitem_url = ""
            replaced_assignment_ids.append(attached.assignment_id)

        assignment.resource_link_id = current_resource_link_id
        assignment.lineitem_url = (user.get("lineitem_url") or assignment.lineitem_url or "").strip()
        _refresh_assignment_configuration(assignment)
        db.commit()
        db.refresh(assignment)
        log_event(
            "assignment.attached_to_activity",
            actor_sub=user.get("sub", ""),
            resource_link_id=assignment.resource_link_id,
            details={
                "assignment_id": assignment.assignment_id,
                "course_id": assignment.course_id,
                "title": assignment.title,
                "replaced_assignment_ids": replaced_assignment_ids,
            },
        )
        payload = _serialize_assignment(assignment)
        payload["replaced_assignment_ids"] = replaced_assignment_ids
        return jsonify(payload)


@assignments_bp.route("/assignments/<assignment_id>/detach-current-activity", methods=["POST"])
def detach_assignment_from_current_activity(assignment_id):
    user, error_response = _require_teacher()
    if error_response:
        return error_response

    current_resource_link_id = (user.get("resource_link_id") or "").strip()
    if not current_resource_link_id:
        return jsonify({"error": "Missing resource link context in session"}), 400

    with _db_session() as db:
        assignment, lookup_error = _get_assignment_owned_by_teacher(db, user, assignment_id)
        if lookup_error:
            return lookup_error

        if assignment.resource_link_id != current_resource_link_id:
            return jsonify({"error": "Assignment is not attached to this activity"}), 409

        assignment.resource_link_id = ""
        assignment.lineitem_url = ""
        db.commit()
        db.refresh(assignment)
        log_event(
            "assignment.detached_from_activity",
            actor_sub=user.get("sub", ""),
            resource_link_id=current_resource_link_id,
            details={
                "assignment_id": assignment.assignment_id,
                "course_id": assignment.course_id,
                "title": assignment.title,
            },
        )
        return jsonify(_serialize_assignment(assignment))


@assignments_bp.route("/assignments/<assignment_id>/starter-upload", methods=["POST"])
def upload_starter_zip(assignment_id):
    user, error_response = _require_teacher()
    if error_response:
        return error_response

    uploaded_file = request.files.get("file")
    with _db_session() as db:
        assignment, lookup_error = _get_assignment_owned_by_teacher(db, user, assignment_id)
        if lookup_error:
            return lookup_error

        try:
            result = save_assignment_archive(uploaded_file, assignment, artifact_kind="starter")
            assignment.starter_zip_path = result["zip_path"]
            assignment.starter_extracted_path = result["extracted_path"]
            assignment.artifacts_validated = bool(assignment.tests_zip_path and assignment.has_required_test_runner)
            assignment.artifact_validation_error = ""
            _refresh_assignment_configuration(assignment)
            db.commit()
            db.refresh(assignment)
            log_event(
                "assignment.starter_uploaded",
                actor_sub=user.get("sub", ""),
                resource_link_id=assignment.resource_link_id,
                details={
                    "assignment_id": assignment.assignment_id,
                    "file_count": result["file_count"],
                },
            )
            return jsonify(_serialize_assignment(assignment))
        except ArtifactValidationError as exc:
            log_event(
                "assignment.upload_validation_failed",
                actor_sub=user.get("sub", ""),
                resource_link_id=assignment.resource_link_id,
                details={"assignment_id": assignment.assignment_id, "artifact": "starter", "error": str(exc)},
            )
            return jsonify({"error": str(exc)}), 400


@assignments_bp.route("/assignments/<assignment_id>/tests-upload", methods=["POST"])
def upload_tests_zip(assignment_id):
    user, error_response = _require_teacher()
    if error_response:
        return error_response

    uploaded_file = request.files.get("file")
    with _db_session() as db:
        assignment, lookup_error = _get_assignment_owned_by_teacher(db, user, assignment_id)
        if lookup_error:
            return lookup_error

        try:
            result = save_assignment_archive(uploaded_file, assignment, artifact_kind="tests")
            assignment.tests_zip_path = result["zip_path"]
            assignment.tests_extracted_path = result["extracted_path"]
            assignment.has_required_test_runner = bool(result["has_required_test_runner"])
            assignment.artifacts_validated = bool(assignment.starter_zip_path and assignment.has_required_test_runner)
            assignment.artifact_validation_error = ""
            _refresh_assignment_configuration(assignment)
            db.commit()
            db.refresh(assignment)
            log_event(
                "assignment.tests_uploaded",
                actor_sub=user.get("sub", ""),
                resource_link_id=assignment.resource_link_id,
                details={
                    "assignment_id": assignment.assignment_id,
                    "file_count": result["file_count"],
                    "has_required_test_runner": result["has_required_test_runner"],
                },
            )
            return jsonify(_serialize_assignment(assignment))
        except ArtifactValidationError as exc:
            log_event(
                "assignment.upload_validation_failed",
                actor_sub=user.get("sub", ""),
                resource_link_id=assignment.resource_link_id,
                details={"assignment_id": assignment.assignment_id, "artifact": "tests", "error": str(exc)},
            )
            return jsonify({"error": str(exc)}), 400


@assignments_bp.route("/assignments/<assignment_id>/artifacts/<artifact_kind>", methods=["DELETE"])
def delete_assignment_artifact(assignment_id, artifact_kind):
    user, error_response = _require_teacher()
    if error_response:
        return error_response

    if artifact_kind not in {"starter", "tests"}:
        return jsonify({"error": "Unsupported artifact type"}), 400

    with _db_session() as db:
        assignment, lookup_error = _get_assignment_owned_by_teacher(db, user, assignment_id)
        if lookup_error:
            return lookup_error

        try:
            clear_assignment_archive(assignment, artifact_kind)
        except ArtifactValidationError as exc:
            return jsonify({"error": str(exc)}), 400

        if artifact_kind == "starter":
            assignment.starter_zip_path = None
            assignment.starter_extracted_path = None
        else:
            assignment.tests_zip_path = None
            assignment.tests_extracted_path = None
            assignment.has_required_test_runner = False

        assignment.artifacts_validated = False
        assignment.artifact_validation_error = ""
        _refresh_assignment_configuration(assignment)
        db.commit()
        db.refresh(assignment)
        log_event(
            "assignment.artifact_deleted",
            actor_sub=user.get("sub", ""),
            resource_link_id=assignment.resource_link_id,
            details={"assignment_id": assignment.assignment_id, "artifact": artifact_kind},
        )
        return jsonify(_serialize_assignment(assignment))


@assignments_bp.route("/assignments/<assignment_id>/artifacts-status", methods=["GET"])
def get_assignment_artifacts_status(assignment_id):
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        assignment = db.get(Assignment, assignment_id)
        if not assignment:
            return jsonify({"error": "Assignment not found"}), 404

        if user.get("role") == "teacher":
            if assignment.course_id != user.get("course_id"):
                return jsonify({"error": "Forbidden"}), 403
        elif assignment.resource_link_id != user.get("resource_link_id"):
            return jsonify({"error": "Forbidden"}), 403

        return jsonify(
            {
                "assignment_id": assignment.assignment_id,
                "starter_zip_uploaded": bool(assignment.starter_zip_path),
                "tests_zip_uploaded": bool(assignment.tests_zip_path),
                "has_required_test_runner": bool(assignment.has_required_test_runner),
                "artifacts_validated": bool(assignment.artifacts_validated),
                "artifact_validation_error": assignment.artifact_validation_error,
                "is_configured": bool(assignment.is_configured),
                "configuration_reasons": _get_assignment_configuration_reasons(assignment),
            }
        )


@assignments_bp.route("/attempts", methods=["POST"])
def create_attempt():
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        assignment = _get_assignment_for_launch(db, user)
        if not assignment or not assignment.is_configured:
            reasons = _get_assignment_configuration_reasons(assignment) if assignment else [
                "No assignment configured for this activity"
            ]
            return jsonify({"error": "Assignment is not configured for this activity", "details": reasons}), 400

        attempt = Attempt(
            user_sub=user["sub"],
            resource_link_id=user["resource_link_id"],
            status="created",
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        try:
            container = create_attempt_container()
            attempt.container_id = container["container_id"]
            attempt.status = container.get("docker_status", "running")
            starter_sync = populate_workspace_from_starter(
                attempt.container_id,
                assignment.starter_extracted_path,
            )
            refresh_attempt_timeout(attempt)
            db.commit()
            db.refresh(attempt)
            log_event(
                "attempt.created",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={
                    "attempt_id": attempt.attempt_id,
                    "container_id": attempt.container_id,
                    "status": attempt.status,
                    "starter_copied": bool(starter_sync.get("copied")),
                    "starter_file_count": int(starter_sync.get("file_count", 0)),
                },
            )
        except Exception as exc:
            attempt.status = "failed"
            db.commit()
            log_event(
                "attempt.create_failed",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={"attempt_id": attempt.attempt_id, "error": str(exc)},
            )
            return jsonify({"error": f"Failed to create attempt container: {exc}"}), 500

        return (
            jsonify(
                {
                    "attempt_id": attempt.attempt_id,
                    "status": attempt.status,
                    "container_id": attempt.container_id,
                    "created_at": attempt.created_at.isoformat(),
                    "last_activity_at": attempt.last_activity_at.isoformat(),
                    "expires_at": attempt.expires_at.isoformat(),
                }
            ),
            201,
        )


@assignments_bp.route("/attempts/<attempt_id>/reset", methods=["POST"])
def reset_attempt(attempt_id):
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        attempt = db.get(Attempt, attempt_id)
        if not attempt:
            return jsonify({"error": "Attempt not found"}), 404
        if not _can_access_attempt(user, attempt):
            return jsonify({"error": "Forbidden"}), 403

        try:
            container = reset_attempt_container(attempt.container_id)
            attempt.container_id = container["container_id"]
            attempt.status = container.get("docker_status", "running")
            assignment = _get_assignment_for_launch(db, user)
            starter_sync = populate_workspace_from_starter(
                attempt.container_id,
                assignment.starter_extracted_path if assignment else None,
            )
            refresh_attempt_timeout(attempt)
            db.commit()
            db.refresh(attempt)
            log_event(
                "attempt.reset",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={
                    "attempt_id": attempt.attempt_id,
                    "container_id": attempt.container_id,
                    "status": attempt.status,
                    "starter_copied": bool(starter_sync.get("copied")),
                    "starter_file_count": int(starter_sync.get("file_count", 0)),
                },
            )
        except Exception as exc:
            log_event(
                "attempt.reset_failed",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={"attempt_id": attempt.attempt_id, "error": str(exc)},
            )
            return jsonify({"error": f"Failed to reset attempt: {exc}"}), 500

        return jsonify(
            {
                "attempt_id": attempt.attempt_id,
                "status": attempt.status,
                "container_id": attempt.container_id,
                "last_activity_at": attempt.last_activity_at.isoformat(),
                "expires_at": attempt.expires_at.isoformat(),
            }
        )


@assignments_bp.route("/attempts/<attempt_id>/terminate", methods=["POST"])
def terminate_attempt(attempt_id):
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        attempt = db.get(Attempt, attempt_id)
        if not attempt:
            return jsonify({"error": "Attempt not found"}), 404
        if not _can_access_attempt(user, attempt):
            return jsonify({"error": "Forbidden"}), 403

        try:
            stopped = terminate_attempt_container(attempt.container_id)
            attempt.status = "terminated"
            attempt.container_id = None
            db.commit()
            log_event(
                "attempt.terminated",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={"attempt_id": attempt.attempt_id, "container_stopped": stopped},
            )
        except Exception as exc:
            log_event(
                "attempt.terminate_failed",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={"attempt_id": attempt.attempt_id, "error": str(exc)},
            )
            return jsonify({"error": f"Failed to terminate attempt: {exc}"}), 500

        return jsonify(
            {
                "attempt_id": attempt.attempt_id,
                "status": attempt.status,
                "container_stopped": stopped,
            }
        )


@assignments_bp.route("/attempts/<attempt_id>", methods=["GET"])
def get_attempt(attempt_id):
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        attempt = db.get(Attempt, attempt_id)
        if not attempt:
            return jsonify({"error": "Attempt not found"}), 404
        if not _can_access_attempt(user, attempt):
            return jsonify({"error": "Forbidden"}), 403

        try:
            runtime_status = get_container_status(attempt.container_id)
            refresh_attempt_timeout(attempt)
            db.commit()
            db.refresh(attempt)
        except Exception as exc:
            return jsonify({"error": f"Failed to get attempt status: {exc}"}), 500

        return jsonify(
            {
                "attempt_id": attempt.attempt_id,
                "status": attempt.status,
                "container_id": attempt.container_id,
                "docker_status": runtime_status.get("docker_status"),
                "created_at": attempt.created_at.isoformat(),
                "last_activity_at": attempt.last_activity_at.isoformat(),
                "expires_at": attempt.expires_at.isoformat(),
            }
        )


@assignments_bp.route("/attempts/<attempt_id>/submit", methods=["POST"])
def submit_attempt(attempt_id):
    user, error_response = _require_student()
    if error_response:
        return error_response

    with _db_session() as db:
        attempt = db.get(Attempt, attempt_id)
        if not attempt:
            return jsonify({"error": "Attempt not found"}), 404
        if not _can_access_attempt(user, attempt):
            return jsonify({"error": "Forbidden"}), 403
        if attempt.status in {"terminated", "expired", "submitted"}:
            return jsonify({"error": "Attempt is no longer active"}), 400

        assignment = _get_assignment_for_launch(db, user)
        if not assignment or not assignment.is_configured:
            reasons = _get_assignment_configuration_reasons(assignment) if assignment else [
                "No assignment configured for this activity"
            ]
            return jsonify({"error": "Assignment is not ready for submission", "details": reasons}), 400

        submission = Submission(
            assignment_id=assignment.assignment_id,
            attempt_id=attempt.attempt_id,
            user_sub=user.get("sub", ""),
            resource_link_id=attempt.resource_link_id,
            status="running",
            score=0.0,
            max_points=assignment.max_points,
            passback_status="not_attempted",
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        log_event(
            "submission.created",
            actor_sub=user.get("sub", ""),
            resource_link_id=attempt.resource_link_id,
            details={"submission_id": submission.submission_id, "attempt_id": attempt.attempt_id},
        )

        try:
            log_event(
                "grading.started",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={"submission_id": submission.submission_id},
            )
            grading = run_grading_for_attempt(assignment, attempt)
            submission.status = grading["status"]
            submission.score = float(grading["score"])
            submission.feedback_stdout = grading["stdout"]
            submission.feedback_stderr = grading["stderr"]
            submission.completed_at = datetime.now(timezone.utc)

            log_event(
                "passback.started",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={"submission_id": submission.submission_id},
            )
            passback = post_grade_with_retry(
                launch_id=user.get("launch_id", ""),
                user_sub=user.get("sub", ""),
                score=submission.score,
                max_points=submission.max_points,
                lineitem_url=assignment.lineitem_url,
            )
            submission.passback_attempts = int(passback.get("attempts", 0))
            submission.passback_completed_at = datetime.now(timezone.utc)
            if passback.get("success"):
                submission.passback_status = "succeeded"
                submission.passback_last_error = ""
                log_event(
                    "passback.succeeded",
                    actor_sub=user.get("sub", ""),
                    resource_link_id=attempt.resource_link_id,
                    details={
                        "submission_id": submission.submission_id,
                        "attempts": submission.passback_attempts,
                    },
                )
            else:
                submission.passback_status = "failed"
                submission.passback_last_error = passback.get("error", "")
                if submission.passback_attempts > 1:
                    log_event(
                        "passback.retried",
                        actor_sub=user.get("sub", ""),
                        resource_link_id=attempt.resource_link_id,
                        details={
                            "submission_id": submission.submission_id,
                            "attempts": submission.passback_attempts,
                        },
                    )
                log_event(
                    "passback.failed",
                    actor_sub=user.get("sub", ""),
                    resource_link_id=attempt.resource_link_id,
                    details={
                        "submission_id": submission.submission_id,
                        "error": submission.passback_last_error,
                        "attempts": submission.passback_attempts,
                    },
                )

            try:
                terminate_attempt_container(attempt.container_id)
            except Exception as term_exc:
                log_event(
                    "attempt.terminate_failed",
                    actor_sub=user.get("sub", ""),
                    resource_link_id=attempt.resource_link_id,
                    details={"attempt_id": attempt.attempt_id, "error": str(term_exc)},
                )
            attempt.container_id = None
            attempt.status = "submitted"

            db.commit()
            db.refresh(submission)
            log_event(
                "grading.completed",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={
                    "submission_id": submission.submission_id,
                    "status": submission.status,
                    "score": submission.score,
                },
            )
            return jsonify(_serialize_submission(submission)), 201
        except Exception as exc:
            submission.status = "error"
            submission.score = 0.0
            submission.feedback_stderr = str(exc)
            submission.completed_at = datetime.now(timezone.utc)
            try:
                terminate_attempt_container(attempt.container_id)
            except Exception as term_exc:
                log_event(
                    "attempt.terminate_failed",
                    actor_sub=user.get("sub", ""),
                    resource_link_id=attempt.resource_link_id,
                    details={"attempt_id": attempt.attempt_id, "error": str(term_exc)},
                )
            attempt.container_id = None
            attempt.status = "submitted"
            db.commit()
            db.refresh(submission)
            log_event(
                "grading.failed",
                actor_sub=user.get("sub", ""),
                resource_link_id=attempt.resource_link_id,
                details={"submission_id": submission.submission_id, "error": str(exc)},
            )
            return jsonify(_serialize_submission(submission)), 500


@assignments_bp.route("/submissions/<submission_id>", methods=["GET"])
def get_submission(submission_id):
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        submission = db.get(Submission, submission_id)
        if not submission:
            return jsonify({"error": "Submission not found"}), 404
        if not _can_access_submission(user, submission):
            return jsonify({"error": "Forbidden"}), 403
        return jsonify(_serialize_submission(submission))


@assignments_bp.route("/attempts/<attempt_id>/submissions", methods=["GET"])
def list_attempt_submissions(attempt_id):
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        attempt = db.get(Attempt, attempt_id)
        if not attempt:
            return jsonify({"error": "Attempt not found"}), 404
        if not _can_access_attempt(user, attempt):
            return jsonify({"error": "Forbidden"}), 403

        submissions = (
            db.query(Submission)
            .filter(Submission.attempt_id == attempt_id)
            .order_by(Submission.created_at.desc())
            .all()
        )
        return jsonify({"items": [_serialize_submission(item) for item in submissions]})
