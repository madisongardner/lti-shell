# LTI-Shell Testing Guide

## Overview

This document describes the testing infrastructure for LTI-Shell, including how to run tests, what is covered, and how to add new tests.

## Test Organization

Tests are located in `tests/unit/` and are organized by component:

| File | Coverage |
|------|----------|
| `test_models.py` | ORM model creation, validation, and queries |
| `test_lti_service.py` | LTI authentication, role determination, claim extraction |
| `test_auth_routes.py` | Authorization checks (`_require_user`, `_require_teacher`, etc.) |
| `test_assignments_routes.py` | Assignment/attempt/submission CRUD endpoints |
| `test_terminal_routes.py` | WebSocket terminal route and command execution |
| `test_grading_service.py` | Grading service (score extraction, timeout detection) |
| `test_docker_service.py` | Docker operations (container creation, cleanup) |
| `test_artifact_service.py` | ZIP validation, artifact extraction |
| `test_route_helpers.py` | Assignment payload validation, due date parsing |

## Prerequisites

Ensure you have the following installed:

```bash
# Python 3.10+
python --version

# Installation
pip install -r backend/requirements.txt
pip install pytest pytest-flask pytest-mock
```

## Running Tests

### Run All Tests

```bash
# From project root
cd /path/to/lti-shell
python -m pytest tests/unit/ -v
```

### Run Specific Test File

```bash
python -m pytest tests/unit/test_models.py -v
```

### Run Specific Test Class

```bash
python -m pytest tests/unit/test_lti_service.py::TestDetermineRole -v
```

### Run Specific Test

```bash
python -m pytest tests/unit/test_lti_service.py::TestDetermineRole::test_instructor_role_detected -v
```

### Run with Coverage Report

```bash
# Install coverage
pip install coverage

# Run with coverage
coverage run -m pytest tests/unit/ -v
coverage report
coverage html
# Open htmlcov/index.html in browser
```

### Run with Output

```bash
# Show print statements
python -m pytest tests/unit/ -v -s

# Show full diffs on assertion failure
python -m pytest tests/unit/ -v --tb=long
```

### Run in Watch Mode (requires pytest-watch)

```bash
pip install pytest-watch
ptw tests/unit/
```

## Test Fixtures

Common fixtures are defined in `tests/conftest.py`:

### `app`
Flask test application with testing configuration.

```python
def test_something(app):
    # app is already configured for testing
    assert app.config['TESTING'] is True
```

### `client`
Flask test client for making HTTP requests.

```python
def test_get_route(client):
    response = client.get('/api/assignments')
    assert response.status_code == 200
```

### `session`
Database session for test queries.

```python
def test_create_assignment(session):
    assignment = Assignment(...)
    session.add(assignment)
    session.commit()
    assert assignment.id is not None
```

### `mock_lti_user`
Mock student user in LTI session.

```python
def test_student_can_list_assignments(client, mock_lti_user):
    with client.session_transaction() as sess:
        sess["user"] = mock_lti_user
    
    response = client.get("/api/assignments")
    assert response.status_code == 200
```

### `mock_lti_teacher`
Mock teacher user in LTI session.

```python
def test_teacher_can_create_assignment(client, mock_lti_teacher):
    with client.session_transaction() as sess:
        sess["user"] = mock_lti_teacher
    
    # Test teacher-only endpoint
```

## Test Categories

### Unit Tests

Fast, isolated tests with mocked dependencies. Target: **< 1 second per test**.

- Test single functions/methods in isolation
- Mock external dependencies (Docker, LMS, database)
- Test both happy path and error cases

Example:
```python
def test_instructor_role_detected():
    """Test that Instructor role maps to 'teacher'."""
    roles = ["http://purl.imsglobal.org/vocab/lis/v2/institution/person#Instructor"]
    assert determine_role(roles) == "teacher"
```

### Integration Tests (in `test_assignments_routes.py`)

Tests that verify components work together. May use:
- Real database (SQLite in-memory during tests)
- Flask test client
- Mocked external services (Docker, LMS)

Example:
```python
def test_create_assignment_as_teacher(client, mock_lti_teacher):
    """Test creating an assignment via API."""
    with client.session_transaction() as sess:
        sess["user"] = mock_lti_teacher
    
    response = client.post(
        "/api/assignments",
        data=json.dumps({"title": "Test", ...}),
        content_type="application/json"
    )
    assert response.status_code == 201
```

## Coverage Goals

- **Overall**: ≥ 75% line coverage
- **Backend services**: ≥ 85% coverage
- **Routes**: ≥ 80% coverage
- **Models**: 100% coverage (simple models)

Track coverage with:
```bash
coverage run -m pytest tests/unit/ && coverage report
```

## Mocking Strategies

### Mocking Database Queries

```python
from unittest.mock import patch, MagicMock

def test_with_mocked_db(client, mock_lti_user):
    with patch("routes.assignments.SessionLocal") as mock_session:
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        # Configure mock behavior
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Test code
```

### Mocking Docker Operations

```python
from unittest.mock import patch, MagicMock

def test_with_mocked_docker():
    with patch("services.docker_service.docker_client") as mock_docker:
        mock_container = MagicMock()
        mock_docker.containers.create.return_value = mock_container
        mock_container.id = "abc123"
        
        # Test code
```

### Mocking LTI/External APIs

```python
with patch("services.lti_ags_service.requests.post") as mock_post:
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"lineitem": "..."}
    
    # Test code
```

## Common Test Patterns

### Testing Authorization (401/403)

```python
def test_unauthenticated_request_returns_401(client):
    """User not in session should get 401."""
    response = client.get("/api/assignments")
    assert response.status_code == 401

def test_student_cannot_create_assignment(client, mock_lti_user):
    """Student role should be denied teacher endpoints."""
    with client.session_transaction() as sess:
        sess["user"] = mock_lti_user
        assert sess["user"]["role"] == "student"
    
    response = client.post("/api/assignments", ...)
    assert response.status_code == 403
```

### Testing Parameter Validation

```python
def test_empty_title_rejected(client, mock_lti_teacher):
    """Empty assignment title should return 400."""
    with client.session_transaction() as sess:
        sess["user"] = mock_lti_teacher
    
    response = client.post(
        "/api/assignments",
        data=json.dumps({"title": "", "instructions": "Test", ...}),
        content_type="application/json"
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "title" in data["error"].lower()
```

### Testing Database Persistence

```python
def test_assignment_persists(session):
    """Assignment created in DB should be queryable."""
    assignment = Assignment(
        instructor_sub="teacher-1",
        course_id="course-1",
        resource_link_id="resource-1",
        title="Test Assignment",
        instructions="Test instructions"
    )
    session.add(assignment)
    session.commit()
    
    retrieved = session.query(Assignment).filter(
        Assignment.title == "Test Assignment"
    ).first()
    
    assert retrieved is not None
    assert retrieved.assignment_id == assignment.assignment_id
```

## Debugging Failed Tests

### With Verbose Output

```bash
python -m pytest tests/unit/test_models.py::TestAssignmentModel::test_assignment_creation -vv -s
```

### With Full Traceback

```bash
python -m pytest tests/unit/ --tb=long
```

### With Debugger (pdb)

```python
import pdb

def test_something(client):
    pdb.set_trace()  # Execution will pause here
    response = client.get("/api/assignments")
```

Then run with `-s` flag:
```bash
python -m pytest tests/unit/ -s
```

### With Print Statements

```bash
python -m pytest tests/unit/ -s  # -s shows print() output
```

## Continuous Integration

Tests should be run in CI/CD pipelines before merging:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    python -m pytest tests/unit/ -v --tb=short
```

## Adding New Tests

### 1. Create Test File

```python
# tests/unit/test_new_feature.py
"""Tests for new feature."""
import pytest

class TestNewFeature:
    """Group related tests."""
    
    def test_happy_path(self):
        """Test the expected behavior."""
        pass
    
    def test_error_case(self):
        """Test error handling."""
        pass
```

### 2. Use Appropriate Fixtures

```python
def test_needs_client(client):
    response = client.get("/api/")

def test_needs_db(session):
    obj = Model(...)
    session.add(obj)

def test_needs_auth(client, mock_lti_user):
    with client.session_transaction() as sess:
        sess["user"] = mock_lti_user
```

### 3. Run Tests Frequently

```bash
# During development
python -m pytest tests/unit/test_new_feature.py -v -s

# After completing feature
python -m pytest tests/unit/ --cov=backend
```

## Known Limitations

1. **WebSocket Testing**: Direct testing of Flask-Sock WebSocket endpoints is limited. Tests use mocks and verify route handlers.

2. **Docker Integration**: Tests mock Docker client. Full integration tests should run against a real Docker daemon.

3. **LTI Authentication**: JWT validation requires actual LTI configuration. Tests mock the validation layer.

4. **Database**: Tests use in-memory SQLite. PostgreSQL-specific SQL may behave differently.

## Troubleshooting

### "No module named 'services'"

Ensure `backend/` is in Python path:
```python
# tests/conftest.py - already included
sys.path.insert(0, str(backend_dir))
```

### "Database session not found"

Ensure fixtures are properly injected:
```python
def test_something(session):  # ✓ session fixture required
    pass

def test_wrong():  # ✗ missing session fixture
    session.add(...)  # ERROR: session not defined
```

### "Attempt to write to read-only database"

Tests should use `TESTING = True` config and in-memory SQLite:
```python
class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/testing/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)
