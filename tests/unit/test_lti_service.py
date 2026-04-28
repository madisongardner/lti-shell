"""Unit tests for LTI service (authentication and claim handling)."""
import pytest

from services.lti_service import (
    determine_role,
    extract_user_data,
    ROLES_CLAIM,
    CONTEXT_CLAIM,
    RESOURCE_LINK_CLAIM,
    AGS_ENDPOINT_CLAIM,
)


class TestDetermineRole:
    """Tests for role determination from LTI claims."""

    def test_instructor_role_detected(self):
        """Test that Instructor role maps to 'teacher'."""
        roles = [
            "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor",
        ]
        assert determine_role(roles) == "teacher"

    def test_instructor_in_path_detected(self):
        """Test that any role containing 'Instructor' maps to 'teacher'."""
        roles = [
            "http://example.com/roles/Instructor",
        ]
        assert determine_role(roles) == "teacher"

    def test_administrator_role_detected(self):
        """Test that Administrator role maps to 'teacher'."""
        roles = [
            "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Administrator",
        ]
        assert determine_role(roles) == "teacher"

    def test_teaching_assistant_detected(self):
        """Test that TeachingAssistant role maps to 'teacher'."""
        roles = [
            "http://purl.imsglobal.org/vocab/lis/v2/institution/person#TeachingAssistant",
        ]
        assert determine_role(roles) == "teacher"

    def test_student_role_maps_to_student(self):
        """Test that only student roles map to 'student'."""
        roles = [
            "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Student",
        ]
        assert determine_role(roles) == "student"

    def test_learner_role_maps_to_student(self):
        """Test that Learner role maps to 'student'."""
        roles = [
            "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Learner",
        ]
        assert determine_role(roles) == "student"

    def test_empty_roles_defaults_to_student(self):
        """Test that empty roles list defaults to 'student'."""
        assert determine_role([]) == "student"

    def test_multiple_roles_instructor_takes_precedence(self):
        """Test that Instructor role takes precedence over Student."""
        roles = [
            "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Student",
            "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor",
        ]
        assert determine_role(roles) == "teacher"


class TestExtractUserData:
    """Tests for extracting user data from LTI launch claims."""

    def test_extract_student_data(self):
        """Test extracting student user data."""
        launch_data = {
            "sub": "user123",
            "name": "Alice Student",
            "email": "alice@example.com",
            ROLES_CLAIM: [
                "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Student"
            ],
            CONTEXT_CLAIM: {
                "id": "course-456",
                "title": "Intro to Bash",
                "label": "BASH101",
            },
            RESOURCE_LINK_CLAIM: {
                "id": "resource-789",
                "title": "Assignment 1",
            },
            AGS_ENDPOINT_CLAIM: {
                "lineitem": "https://moodle.example.com/ags/lineitem/1",
                "lineitems": "https://moodle.example.com/ags/lineitems",
                "scope": ["https://purl.imsglobal.org/spec/lti-ags/scope/lineitem"],
            },
        }

        user = extract_user_data(launch_data, "launch-id-001")

        assert user["sub"] == "user123"
        assert user["name"] == "Alice Student"
        assert user["role"] == "student"
        assert user["course_id"] == "course-456"
        assert user["resource_link_id"] == "resource-789"
        assert user["launch_id"] == "launch-id-001"

    def test_extract_teacher_data(self):
        """Test extracting teacher user data."""
        launch_data = {
            "sub": "teacher123",
            "name": "Bob Teacher",
            "email": "bob@example.com",
            ROLES_CLAIM: [
                "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor"
            ],
            CONTEXT_CLAIM: {
                "id": "course-456",
                "title": "Intro to Bash",
            },
            RESOURCE_LINK_CLAIM: {
                "id": "resource-789",
                "title": "Assignment 1",
            },
            AGS_ENDPOINT_CLAIM: {
                "lineitem": "https://moodle.example.com/ags/lineitem/99",
                "scope": ["https://purl.imsglobal.org/spec/lti-ags/scope/lineitem"],
            },
        }

        user = extract_user_data(launch_data, "launch-id-002")

        assert user["role"] == "teacher"
        assert user["name"] == "Bob Teacher"

    def test_extract_handles_missing_fields(self):
        """Test that extraction handles missing optional fields gracefully."""
        launch_data = {
            "sub": "user999",
            # minimal data
        }

        user = extract_user_data(launch_data, "launch-id-003")

        assert user["sub"] == "user999"
        assert user["name"] == "Unknown User"
        assert user["email"] == ""
        assert user["course_id"] == ""
        assert user["resource_link_id"] == ""
        assert user["role"] == "student"  # default

    def test_extract_empty_ags_endpoint(self):
        """Test extraction when AGS endpoint is missing."""
        launch_data = {
            "sub": "user123",
            "name": "Test User",
            ROLES_CLAIM: ["http://example.com/person#Student"],
            CONTEXT_CLAIM: {"id": "course-1"},
            RESOURCE_LINK_CLAIM: {"id": "resource-1"},
            # No AGS_ENDPOINT_CLAIM
        }

        user = extract_user_data(launch_data, "launch-id-004")

        assert user["lineitem_url"] == ""
        assert user["ags_scopes"] == []

    def test_extract_multiple_scopes(self):
        """Test extraction of multiple AGS scopes."""
        launch_data = {
            "sub": "user123",
            AGS_ENDPOINT_CLAIM: {
                "scope": [
                    "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem",
                    "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem.readonly",
                ],
            },
        }

        user = extract_user_data(launch_data, "launch-id-005")

        assert len(user["ags_scopes"]) == 2

    def test_extract_stores_launch_id(self):
        """Test that launch_id is stored in extracted data."""
        launch_data = {"sub": "user123"}

        user = extract_user_data(launch_data, "unique-launch-id-xyz")

        assert user["launch_id"] == "unique-launch-id-xyz"

    def test_extract_course_details(self):
        """Test extraction of complete course context."""
        launch_data = {
            "sub": "user123",
            CONTEXT_CLAIM: {
                "id": "course-abc",
                "title": "Advanced Python",
                "label": "CS201",
            },
        }

        user = extract_user_data(launch_data, "launch-1")

        assert user["course_id"] == "course-abc"
        assert user["course_title"] == "Advanced Python"
        assert user["course_label"] == "CS201"

    def test_extract_resource_link_details(self):
        """Test extraction of resource link information."""
        launch_data = {
            "sub": "user123",
            RESOURCE_LINK_CLAIM: {
                "id": "rl-123",
                "title": "Quiz 2",
            },
        }

        user = extract_user_data(launch_data, "launch-1")

        assert user["resource_link_id"] == "rl-123"
        assert user["resource_link_title"] == "Quiz 2"

    def test_extract_preserves_raw_roles(self):
        """Test that raw roles are preserved for auditing."""
        roles = [
            "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor",
            "http://example.com/custom/role#Admin",
        ]
        launch_data = {
            "sub": "user123",
            ROLES_CLAIM: roles,
        }

        user = extract_user_data(launch_data, "launch-1")

        assert user["roles_raw"] == roles
