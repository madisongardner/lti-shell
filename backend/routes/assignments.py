from contextlib import contextmanager
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database import SessionLocal
from models.assignment import Assignment
from models.attempt import Attempt
from services.docker_service import (
    create_attempt_container,
    get_container_status,
    reset_attempt_container,
    terminate_attempt_container,
)
from services.attempt_cleanup_service import refresh_attempt_timeout
from services.audit_service import log_event

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


def _serialize_assignment(assignment):
    return {
        "assignment_id": assignment.assignment_id,
        "instructor_sub": assignment.instructor_sub,
        "course_id": assignment.course_id,
        "resource_link_id": assignment.resource_link_id,
        "title": assignment.title,
        "instructions": assignment.instructions,
        "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
        "max_points": assignment.max_points,
        "is_configured": assignment.is_configured,
        "created_at": assignment.created_at.isoformat(),
        "updated_at": assignment.updated_at.isoformat(),
    }


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
        "is_configured": True,
    }


def _get_assignment_for_launch(db, user):
    return (
        db.query(Assignment)
        .filter(Assignment.course_id == user.get("course_id", ""))
        .filter(Assignment.resource_link_id == user.get("resource_link_id", ""))
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
            title=validated["title"],
            instructions=validated["instructions"],
            due_at=validated["due_at"],
            max_points=validated["max_points"],
            is_configured=validated["is_configured"],
        )
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
        assignment = db.get(Assignment, assignment_id)
        if not assignment:
            return jsonify({"error": "Assignment not found"}), 404
        if assignment.course_id != user.get("course_id"):
            return jsonify({"error": "Forbidden"}), 403

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

            assignment.is_configured = bool(
                assignment.title.strip() and assignment.instructions.strip() and assignment.max_points > 0
            )
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


@assignments_bp.route("/attempts", methods=["POST"])
def create_attempt():
    user, error_response = _require_user()
    if error_response:
        return error_response

    with _db_session() as db:
        assignment = _get_assignment_for_launch(db, user)
        if not assignment or not assignment.is_configured:
            return jsonify({"error": "Assignment is not configured for this activity"}), 400

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
