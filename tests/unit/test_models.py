"""Unit tests for ORM models."""
from datetime import datetime, timezone
import json

import pytest

from models.assignment import Assignment
from models.attempt import Attempt
from models.submission import Submission
from models.audit_log import AuditLog


class TestAssignmentModel:
    """Tests for Assignment model."""

    def test_assignment_creation(self, session):
        """Test creating an Assignment with all required fields."""
        now = datetime.now(timezone.utc)
        assignment = Assignment(
            instructor_sub="teacher-1",
            course_id="course-1",
            resource_link_id="resource-1",
            title="Bash Basics",
            instructions="Learn shell scripting",
            due_at=now,
            max_points=100.0
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)

        assert assignment.assignment_id is not None
        assert assignment.title == "Bash Basics"
        assert assignment.max_points == 100.0
        assert assignment.is_configured is False  # Default

    def test_assignment_defaults(self, session):
        """Test Assignment default values."""
        assignment = Assignment(
            instructor_sub="teacher-1",
            course_id="course-1",
            resource_link_id="resource-1",
            title="Test",
            instructions="Test instructions"
        )
        session.add(assignment)
        session.commit()

        assert assignment.is_configured is False
        assert assignment.max_points == 100.0
        assert assignment.created_at is not None
        assert assignment.updated_at is not None
        assert assignment.grading_feature == "script_zip"

    def test_assignment_timestamps_set(self, session):
        """Test that timestamps are automatically set."""
        assignment = Assignment(
            instructor_sub="teacher-1",
            course_id="course-1",
            resource_link_id="resource-1",
            title="Test",
            instructions="Test"
        )
        session.add(assignment)
        session.commit()

        assert assignment.created_at is not None
        assert assignment.updated_at is not None
        assert isinstance(assignment.created_at, datetime)

    def test_assignment_artifact_paths(self, session):
        """Test assigning artifact paths."""
        assignment = Assignment(
            instructor_sub="teacher-1",
            course_id="course-1",
            resource_link_id="resource-1",
            title="Test",
            instructions="Test",
            starter_zip_path="/path/to/starter.zip",
            tests_zip_path="/path/to/tests.zip"
        )
        session.add(assignment)
        session.commit()

        assert assignment.starter_zip_path == "/path/to/starter.zip"
        assert assignment.tests_zip_path == "/path/to/tests.zip"

    def test_assignment_query_by_course_and_resource(self, session):
        """Test querying assignments by course and resource link."""
        a1 = Assignment(
            instructor_sub="teacher-1",
            course_id="course-1",
            resource_link_id="resource-1",
            title="Assignment 1",
            instructions="Test"
        )
        a2 = Assignment(
            instructor_sub="teacher-1",
            course_id="course-2",
            resource_link_id="resource-1",
            title="Assignment 2",
            instructions="Test"
        )
        session.add_all([a1, a2])
        session.commit()

        result = session.query(Assignment).filter(
            Assignment.course_id == "course-1",
            Assignment.resource_link_id == "resource-1"
        ).first()

        assert result.assignment_id == a1.assignment_id
        assert result.title == "Assignment 1"


class TestAttemptModel:
    """Tests for Attempt model."""

    def test_attempt_creation(self, session):
        """Test creating an Attempt."""
        attempt = Attempt(
            user_sub="student-1",
            resource_link_id="resource-1",
            container_id="container-abc123",
            status="active"
        )
        session.add(attempt)
        session.commit()
        session.refresh(attempt)

        assert attempt.attempt_id is not None
        assert attempt.container_id == "container-abc123"
        assert attempt.status == "active"

    def test_attempt_status_tracking(self, session):
        """Test attempt status transitions."""
        attempt = Attempt(
            user_sub="student-1",
            resource_link_id="resource-1",
            container_id="container-abc",
            status="active"
        )
        session.add(attempt)
        session.commit()

        attempt.status = "submitted"
        session.commit()
        session.refresh(attempt)

        assert attempt.status == "submitted"

    def test_attempt_expiration_timestamp(self, session):
        """Test attempt expiration tracking."""
        now = datetime.now(timezone.utc)
        attempt = Attempt(
            user_sub="student-1",
            resource_link_id="resource-1",
            container_id="container-abc",
            status="active",
            expires_at=now
        )
        session.add(attempt)
        session.commit()

        assert attempt.expires_at is not None

    def test_attempt_defaults(self, session):
        """Test Attempt default values."""
        attempt = Attempt(
            user_sub="student-1",
            resource_link_id="resource-1",
            container_id="container-abc"
        )
        session.add(attempt)
        session.commit()

        assert attempt.status in ["active", "created"]  # Default statuses
        assert attempt.created_at is not None

    def test_attempt_query_by_user_and_resource(self, session):
        """Test querying attempts by user and resource link."""
        att1 = Attempt(
            user_sub="student-1",
            resource_link_id="resource-1",
            container_id="container-1"
        )
        att2 = Attempt(
            user_sub="student-2",
            resource_link_id="resource-1",
            container_id="container-2"
        )
        session.add_all([att1, att2])
        session.commit()

        result = session.query(Attempt).filter(
            Attempt.user_sub == "student-1",
            Attempt.resource_link_id == "resource-1"
        ).first()

        assert result.attempt_id == att1.attempt_id


class TestSubmissionModel:
    """Tests for Submission model."""

    def test_submission_creation(self, session):
        """Test creating a Submission."""
        submission = Submission(
            assignment_id="assignment-1",
            attempt_id="attempt-1",
            user_sub="student-1",
            resource_link_id="resource-1",
            status="graded",
            score=85.0,
            max_points=100.0
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)

        assert submission.submission_id is not None
        assert submission.score == 85.0

    def test_submission_feedback_storage(self, session):
        """Test storing stdout/stderr feedback."""
        submission = Submission(
            assignment_id="assignment-1",
            attempt_id="attempt-1",
            user_sub="student-1",
            resource_link_id="resource-1",
            status="graded",
            score=60.0,
            max_points=100.0,
            feedback_stdout="Test passed: 6/10",
            feedback_stderr="Warning: slow execution"
        )
        session.add(submission)
        session.commit()

        assert submission.feedback_stdout == "Test passed: 6/10"
        assert submission.feedback_stderr == "Warning: slow execution"

    def test_submission_passback_fields(self, session):
        """Test passback tracking fields."""
        submission = Submission(
            assignment_id="assignment-1",
            attempt_id="attempt-1",
            user_sub="student-1",
            resource_link_id="resource-1",
            status="graded",
            score=90.0,
            max_points=100.0,
            passback_status="succeeded",
            passback_attempts=1
        )
        session.add(submission)
        session.commit()

        assert submission.passback_status == "succeeded"
        assert submission.passback_attempts == 1

    def test_submission_status_validation(self, session):
        """Test submission status transitions."""
        submission = Submission(
            assignment_id="assignment-1",
            attempt_id="attempt-1",
            user_sub="student-1",
            resource_link_id="resource-1",
            status="grading"
        )
        session.add(submission)
        session.commit()

        # Update status
        submission.status = "graded"
        session.commit()

        assert submission.status == "graded"

    def test_submission_timestamps(self, session):
        """Test submission timestamp tracking."""
        submission = Submission(
            assignment_id="assignment-1",
            attempt_id="attempt-1",
            user_sub="student-1",
            resource_link_id="resource-1",
            status="pending"
        )
        session.add(submission)
        session.commit()

        assert submission.created_at is not None


class TestAuditLogModel:
    """Tests for AuditLog model."""

    def test_audit_log_creation(self, session):
        """Test creating an audit log entry."""
        log = AuditLog(
            event_type="assignment.created",
            actor_sub="teacher-1",
            resource_link_id="resource-1",
            details_json=json.dumps({"assignment_id": "id-1"})
        )
        session.add(log)
        session.commit()
        session.refresh(log)

        assert log.id is not None
        assert log.event_type == "assignment.created"
        assert log.actor_sub == "teacher-1"

    def test_audit_log_details_json(self, session):
        """Test storing and retrieving JSON details."""
        details = {
            "assignment_id": "assignment-1",
            "title": "Bash Scripting",
            "max_points": 100.0
        }
        log = AuditLog(
            event_type="assignment.created",
            actor_sub="teacher-1",
            resource_link_id="resource-1",
            details_json=json.dumps(details)
        )
        session.add(log)
        session.commit()
        session.refresh(log)

        parsed = json.loads(log.details_json)
        assert parsed["assignment_id"] == "assignment-1"

    def test_audit_log_timestamp(self, session):
        """Test that timestamps are set."""
        log = AuditLog(
            event_type="submission.graded",
            actor_sub="system",
            resource_link_id="resource-1"
        )
        session.add(log)
        session.commit()

        assert log.created_at is not None

    def test_audit_log_query_by_event(self, session):
        """Test querying logs by event type."""
        log1 = AuditLog(
            event_type="assignment.created",
            actor_sub="teacher-1",
            resource_link_id="resource-1"
        )
        log2 = AuditLog(
            event_type="attempt.created",
            actor_sub="student-1",
            resource_link_id="resource-1"
        )
        session.add_all([log1, log2])
        session.commit()

        results = session.query(AuditLog).filter(
            AuditLog.event_type == "assignment.created"
        ).all()

        assert len(results) == 1
        assert results[0].event_type == "assignment.created"

    def test_audit_log_query_by_actor(self, session):
        """Test querying logs by actor."""
        log1 = AuditLog(
            event_type="attempt.created",
            actor_sub="student-1",
            resource_link_id="resource-1"
        )
        log2 = AuditLog(
            event_type="attempt.created",
            actor_sub="student-2",
            resource_link_id="resource-1"
        )
        session.add_all([log1, log2])
        session.commit()

        results = session.query(AuditLog).filter(
            AuditLog.actor_sub == "student-1"
        ).all()

        assert len(results) == 1
