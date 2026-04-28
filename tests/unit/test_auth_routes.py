"""Unit tests for authorization checks in routes."""
import pytest
from flask import session as flask_session, json

from routes.assignments import (
    _require_user,
    _require_teacher,
    _require_student,
    _can_access_attempt,
    _can_access_submission,
)


class TestRequireUser:
    """Tests U34-U35: User authentication requirement."""

    def test_no_user_returns_401(self, client):
        """U34: No user in session returns 401."""
        with client.session_transaction() as sess:
            sess.clear()

        user, error = _require_user()
        assert user is None
        assert error[1] == 401
        assert "Not authenticated" in error[0].get_json()["error"]

    def test_user_without_launch_context_returns_400(self, client):
        """U35: User without resource_link_id returns 400."""
        with client.session_transaction() as sess:
            sess["user"] = {"sub": "user-1"}  # Missing resource_link_id

        user, error = _require_user()
        assert user is None
        assert error[1] == 400
        assert "launch context" in error[0].get_json()["error"]

    def test_valid_user_returns_user(self, client, mock_lti_user):
        """Test that valid user with context is returned."""
        with client.session_transaction() as sess:
            sess["user"] = mock_lti_user

        user, error = _require_user()
        assert user is not None
        assert user["sub"] == "user-123"
        assert error is None


class TestRequireTeacher:
    """Tests U36: Teacher role requirement."""

    def test_student_cannot_access_teacher_endpoint(self, client, mock_lti_user):
        """U36: Student role returns 403 on teacher-only endpoint."""
        with client.session_transaction() as sess:
            sess["user"] = mock_lti_user
            assert sess["user"]["role"] == "student"

        user, error = _require_teacher()
        assert user is None
        assert error[1] == 403
        assert "Teacher access required" in error[0].get_json()["error"]

    def test_teacher_can_access(self, client, mock_lti_teacher):
        """Test that teacher role can access teacher endpoints."""
        with client.session_transaction() as sess:
            sess["user"] = mock_lti_teacher

        user, error = _require_teacher()
        assert user is not None
        assert user["role"] == "teacher"
        assert error is None

    def test_teacher_without_course_context_returns_400(self, client, mock_lti_teacher):
        """Test that teacher without course_id returns 400."""
        teacher = mock_lti_teacher.copy()
        del teacher["course_id"]

        with client.session_transaction() as sess:
            sess["user"] = teacher

        user, error = _require_teacher()
        assert error[1] == 400
        assert "course context" in error[0].get_json()["error"]


class TestRequireStudent:
    """Tests for student role requirement."""

    def test_teacher_cannot_be_student(self, client, mock_lti_teacher):
        """Test that teacher role is rejected from student endpoints."""
        with client.session_transaction() as sess:
            sess["user"] = mock_lti_teacher

        user, error = _require_student()
        assert user is None
        assert error[1] == 403
        assert "Student access required" in error[0].get_json()["error"]

    def test_student_can_access(self, client, mock_lti_user):
        """Test that student role can access student endpoints."""
        with client.session_transaction() as sess:
            sess["user"] = mock_lti_user

        user, error = _require_student()
        assert user is not None
        assert user["role"] == "student"
        assert error is None


class TestCanAccessAttempt:
    """Tests U37: Cross-resource access control for attempts."""

    def test_student_can_access_own_attempt(self):
        """U37a: Student can access own attempt in same resource."""
        user = {
            "sub": "student-1",
            "resource_link_id": "resource-1",
            "role": "student"
        }
        attempt = type("A", (), {
            "user_sub": "student-1",
            "resource_link_id": "resource-1"
        })()

        assert _can_access_attempt(user, attempt) is True

    def test_student_cannot_access_others_attempt(self):
        """U37b: Student cannot access another student's attempt."""
        user = {
            "sub": "student-1",
            "resource_link_id": "resource-1",
            "role": "student"
        }
        attempt = type("A", (), {
            "user_sub": "student-2",
            "resource_link_id": "resource-1"
        })()

        assert _can_access_attempt(user, attempt) is False

    def test_student_cannot_access_different_resource_attempt(self):
        """U37c: Student cannot access attempt from different resource link."""
        user = {
            "sub": "student-1",
            "resource_link_id": "resource-1",
            "role": "student"
        }
        attempt = type("A", (), {
            "user_sub": "student-1",
            "resource_link_id": "resource-2"  # Different resource
        })()

        assert _can_access_attempt(user, attempt) is False

    def test_teacher_can_access_attempts_in_resource(self):
        """Test that teacher can access any student's attempt in their resource."""
        user = {
            "sub": "teacher-1",
            "resource_link_id": "resource-1",
            "role": "teacher"
        }
        attempt = type("A", (), {
            "user_sub": "student-1",
            "resource_link_id": "resource-1"
        })()

        assert _can_access_attempt(user, attempt) is True

    def test_teacher_cannot_access_different_resource_attempts(self):
        """Test that teacher cannot access attempts from different resource link."""
        user = {
            "sub": "teacher-1",
            "resource_link_id": "resource-1",
            "role": "teacher"
        }
        attempt = type("A", (), {
            "user_sub": "student-1",
            "resource_link_id": "resource-2"  # Different resource
        })()

        assert _can_access_attempt(user, attempt) is False


class TestCanAccessSubmission:
    """Tests for submission access control."""

    def test_student_can_access_own_submission(self):
        """Test that student can access their own submission."""
        user = {
            "sub": "student-1",
            "resource_link_id": "resource-1",
            "role": "student"
        }
        submission = type("S", (), {
            "user_sub": "student-1",
            "resource_link_id": "resource-1"
        })()

        assert _can_access_submission(user, submission) is True

    def test_student_cannot_access_others_submission(self):
        """Test that student cannot access another student's submission."""
        user = {
            "sub": "student-1",
            "resource_link_id": "resource-1",
            "role": "student"
        }
        submission = type("S", (), {
            "user_sub": "student-2",
            "resource_link_id": "resource-1"
        })()

        assert _can_access_submission(user, submission) is False

    def test_teacher_can_access_submissions_in_resource(self):
        """Test that teacher can view any student's submission in their resource."""
        user = {
            "sub": "teacher-1",
            "resource_link_id": "resource-1",
            "role": "teacher"
        }
        submission = type("S", (), {
            "user_sub": "student-1",
            "resource_link_id": "resource-1"
        })()

        assert _can_access_submission(user, submission) is True

    def test_submission_access_respects_resource_boundary(self):
        """Test that submission access is restricted to resource link."""
        user = {
            "sub": "teacher-1",
            "resource_link_id": "resource-1",
            "role": "teacher"
        }
        submission = type("S", (), {
            "user_sub": "student-1",
            "resource_link_id": "resource-2"  # Different resource
        })()

        assert _can_access_submission(user, submission) is False


class TestAuthorizationIntegration:
    """Integration tests for authorization in API endpoints."""

    def test_unauthenticated_request_to_assignments(self, client):
        """Test that unauthenticated requests to /api/assignments return 401."""
        response = client.get("/api/assignments")
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "Not authenticated" in data["error"]

    def test_authenticated_student_gets_their_assignments(self, client, mock_lti_user):
        """Test that authenticated student can list assignments for their course."""
        with client.session_transaction() as sess:
            sess["user"] = mock_lti_user

        # This will 404 because no assignments exist, but auth should pass
        response = client.get("/api/assignments")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "items" in data

    def test_cross_course_isolation(self, client, mock_lti_user):
        """Test that student only sees assignments from their course."""
        # This is a placeholder for a full integration test
        # In practice, you'd create assignments in different courses
        # and verify filtering works
        pass

    def test_teacher_sees_all_course_assignments(self, client, mock_lti_teacher):
        """Test that teacher sees all assignments in their course."""
        with client.session_transaction() as sess:
            sess["user"] = mock_lti_teacher

        # Teacher should be able to list assignments
        response = client.get("/api/assignments")
        assert response.status_code == 200
