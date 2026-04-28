# LTI-Shell End-to-End Demo Guide

**Target Audience**: CS students/faculty (10-minute classroom presentation)  
**Goal**: Show how an LTI 1.3 external tool integrates with LMS, provides secure coding sandboxes, and automates grading.

---

## Part 1: Architecture Overview (30 seconds)

### What to Say Out Loud

> *"LTI-Shell is a Bash sandbox environment integrated into Moodle using the LTI 1.3 standard. Here's the architecture:*
> 
> - **Frontend**: HTML/JavaScript dashboards for teachers and students
> - **Backend**: Flask web server handling LTI authentication and API requests
> - **Docker**: Isolated Linux containers providing secure Bash sandboxes
> - **Database**: SQLite (dev) or PostgreSQL (production) for assignments, attempts, submissions
> - **Moodle Integration**: Uses OAuth 2.0 + JWT for authentication and LTI AGS for grade passback"*

### What's Happening Behind the Scenes

```
┌─────────────┐         ┌──────────────┐         ┌───────────┐
│   Moodle    │◄───────►│ LTI-Shell    │◄──────IP→│  Docker   │
│   (LMS)     │ OIDC    │  (Flask)     │  Docker  │ Containers
│             │ + JWT   │              │  API     │           
│ OAuth SP    │◄───────►│ OAuth Client │          └───────────┘
└─────────────┘         └──────────────┘              
                             │
                             │
                        ┌────▼─────┐
                        │ Database  │
                        │ SQLite/PG │
                        └───────────┘
```

**Key Components**:
- **pylti1p3 library**: Handles LTI 1.3 flow (OIDC login, JWT validation, role detection)
- **Flask-Session**: Persists user claims (role, course_id, resource_link_id) in server-side sessions
- **Docker SDK**: Manages container lifecycle (create, exec, terminate)
- **SQLAlchemy ORM**: Models for assignments, attempts, submissions, audit logs

---

## Part 2: TEACHER WORKFLOW - Demo Flow

### Step 1: Teacher Launches into Moodle → LTI-Shell

#### What to Say Out Loud

> *"Let me open Moodle and click on the LTI-Shell activity in a course. This launches the LTI authentication flow."*

**Demo Action**: Click the LTI activity link in Moodle and observe the redirect sequence.

#### What's Happening Behind the Scenes

**LTI 1.3 OIDC Login Flow** (3-step handshake):

```
1. BROWSER requests: https://moodle.example.com/lti/activity
   ↓
   Moodle → Browser redirect to: https://lti-shell.example.com/lti/login
   + Query params: iss, login_hint, target_link_uri, lti_message_hint
   
2. LTI-Shell /lti/login endpoint:
   - Extracts target_link_uri (where to return after auth)
   - Creates OIDC login with llm1p3 library
   - Redirects browser → Moodle's OAuth authorization endpoint
   - Browser → Moodle login (user authenticates if not already logged in)
   - Moodle asks user: "Allow LTI-Shell to access your account?"
   
3. Moodle redirects browser → LTI-Shell /lti/launch (POST)
   - Body contains: signed JWT token with all LTI claims
   - JWT includes: sub, name, email, roles, course_id, resource_link_id, ags_endpoint, etc.
   - pylti1p3 validates JWT signature using Moodle's public key
   - JWT expires in ~5 minutes (prevents replay attacks)
```

**Key Security Points**:
- ✓ SSL/TLS encryption (HTTPS only)
- ✓ JWT cryptographic signature (RSA-256)
- ✓ Token expiration window (5 min)
- ✓ `iss` (issuer) validation ensures only trusted Moodle instances

---

### Step 2: LTI-Shell Extracts User Role and Redirects

#### What to Say Out Loud

> *"The system validates the JWT, extracts your role (teacher, student, admin), and routes you to the appropriate dashboard."*

**Demo Action**: Screen transitions to teacher dashboard. Point out the header: "Teacher Dashboard - [Your Name]"

#### What's Happening Behind the Scenes

**File**: `routes/lti.py` → `/lti/launch` endpoint

```python
# JWT validation (automatic with pylti1p3)
launch_data = message_launch.get_launch_data()
# Returns dict with LTI claims

# Extract user data using service
session['user'] = extract_user_data(launch_data, launch_id)
# Calls services/lti_service.py::determine_role()

# determine_role logic:
def determine_role(roles_list):
    for role_uri in roles_list:
        if 'Instructor' in role_uri or 'Administrator' in role_uri:
            return 'teacher'
    return 'student'

# Redirect based on role
if session['user']['role'] == 'teacher':
    return redirect('/pages/teacher-dashboard.html')
else:
    return redirect('/pages/student-dashboard.html')
```

**Session State** (persisted in Flask-Session):
```python
session['user'] = {
    'sub': 'moodle_user_id_12345',           # Unique user ID from Moodle
    'name': 'Dr. Jane Smith',
    'email': 'j.smith@example.com',
    'role': 'teacher',
    'course_id': 'course_89101',             # Moodle course ID
    'resource_link_id': 'activity_link_202', # Unique LTI activity ID
    'lineitem_url': 'https://moodle.../ags/lineitem/1',  # Grade passback URL
    'launch_id': 'unique_launch_xyz'         # For later AGS token retrieval
}
```

---

### Step 3: Teacher Sees Dashboard and Creates Assignment

#### What to Say Out Loud

> *"As a teacher, I can now create a new assignment. I set the title, instructions, due date, and point value. Then I upload two files: the starter code (template) and the test suite."*

**Demo Action**:
1. Click "Create Assignment"
2. Fill in:
   - Title: "Bash String Manipulation"
   - Instructions: "Write a script that reverses a string"
   - Due Date: 2 weeks from now
   - Max Points: 100
3. Click "Create"

#### What's Happening Behind the Scenes

**Endpoint**: `POST /api/assignments`

```python
# Route validates teacher role (403 if student)
user, error = _require_teacher()

# Extract and validate payload
payload = request.get_json()
validated = _validate_assignment_payload(payload)
# Checks: title not empty, instructions not empty, max_points > 0, due_at is ISO 8601 string

# Create Assignment model
assignment = Assignment(
    instructor_sub=user['sub'],        # DB tracks WHO created this
    course_id=user['course_id'],       # DB enforces course isolation
    resource_link_id=user['resource_link_id'],  # Only this LTI activity can use it
    title="Bash String Manipulation",
    instructions="...",
    due_at=2026-05-15T23:59:00Z,      # Parsed and stored with timezone
    max_points=100.0
)
session.add(assignment)
session.commit()

# Log event for audit trail
log_event(
    'assignment.created',
    actor_sub=user['sub'],
    resource_link_id=assignment.resource_link_id,
    details={'assignment_id': assignment.assignment_id, 'title': assignment.title}
)

# Return 201 with assignment data
return jsonify(_serialize_assignment(assignment)), 201
```

**Database Record** (`assignments` table):
```sql
INSERT INTO assignments (
  assignment_id, instructor_sub, course_id, resource_link_id,
  title, instructions, due_at, max_points, is_configured, ...
) VALUES (
  'uuid-abc123', 'moodle_user_12345', 'course_89101', 'activity_link_202',
  'Bash String Manipulation', '...', '2026-05-15T23:59:00+00:00', 100.0, FALSE, ...
);
```

**Audit Trail** (`audit_logs` table):
```json
{
  "event_type": "assignment.created",
  "actor_sub": "moodle_user_12345",
  "resource_link_id": "activity_link_202",
  "details_json": "{\"assignment_id\": \"uuid-abc123\", \"title\": \"Bash String Manipulation\"}"
}
```

---

### Step 4: Teacher Uploads Starter Code and Tests

#### What to Say Out Loud

> *"Now I upload two ZIP files:*
> 
> 1. **Starter ZIP**: Contains template code that students start with (e.g., hello.sh with function signatures)
> 2. **Tests ZIP**: Contains run_tests.sh that I write to test student submissions"*

**Demo Action**:
1. Click "Upload Starter ZIP" → Select `starter.zip`
2. Click "Upload Tests ZIP" → Select `tests.zip`
3. Observe status: `is_configured: true` ✓

#### What's Happening Behind the Scenes

**Endpoint**: `POST /api/assignments/<id>/starter-upload` or `tests-upload`

```python
# File upload with validation
def upload_starter(assignment_id):
    user = _require_teacher()
    assignment = _get_assignment_owned_by_teacher(db, user, assignment_id)
    
    file = request.files.get('file')
    if not file or file.filename == '':
        return 400
    
    # Save multipart upload to temp location
    temp_path = f'/tmp/upload_{uuid4()}.zip'
    file.save(temp_path)
    
    # Validate and extract ZIP
    try:
        save_assignment_archive(
            archive_path=temp_path,
            artifact_type='starter',
            assignment=assignment
        )
    except ArtifactValidationError as exc:
        return 400, {"error": str(exc)}
    
    # Update assignment record
    assignment.starter_zip_path = f'/data/artifacts/{assignment_id}/starter.zip'
    assignment.starter_extracted_path = f'/data/artifacts/{assignment_id}/starter/'
    session.commit()
    
    return 200
```

**Artifact Validation** (`services/assignment_artifact_service.py`):

```python
def save_assignment_archive(archive_path, artifact_type, assignment):
    # 1. Check ZIP size (max 50 MB)
    if os.path.getsize(archive_path) > 50_000_000:
        raise ArtifactValidationError("ZIP too large")
    
    # 2. Check for symlinks (security issue)
    with zipfile.ZipFile(archive_path) as zf:
        for info in zf.infolist():
            if info.is_symlink():
                raise ArtifactValidationError("Symlinks not allowed")
    
    # 3. Check for path traversal (../../../etc/passwd)
    for name in zf.namelist():
        if '..' in name:
            raise ArtifactValidationError("Path traversal detected")
    
    # 4. Extract to /data/artifacts/{assignment_id}/{artifact_type}/
    extract_path = f'/data/artifacts/{assignment.assignment_id}/{artifact_type}/'
    zf.extractall(extract_path)
    
    # 5. For tests ZIP, verify run_tests.sh exists
    if artifact_type == 'tests':
        if not os.path.exists(f'{extract_path}/run_tests.sh'):
            raise ArtifactValidationError("tests.zip must contain run_tests.sh")
        assignment.has_required_test_runner = True
    
    assignment.artifacts_validated = True
    # Update is_configured flag based on remaining requirements
```

**Filesystem After Upload**:
```
/data/artifacts/
└── uuid-abc123/
    ├── starter/
    │   ├── hello.sh          # Template function
    │   └── README.md
    └── tests/
        ├── run_tests.sh      # Test runner script
        └── test_data/
            └── test_cases.txt
```

**Assignment Status Update**:
- `starter_uploaded`: TRUE
- `tests_uploaded`: TRUE
- `has_required_test_runner`: TRUE
- `artifacts_validated`: TRUE
- `is_configured`: TRUE ✓

Now students can see this assignment!

---

## Part 3: STUDENT WORKFLOW - Live Demo

### Step 5: Student Launches into Moodle → LTI-Shell

#### What to Say Out Loud

> *"Let me switch to a student account. I click the same LTI-Shell activity link, and I go through the same LTI authentication flow—but I see the STUDENT dashboard instead."*

**Demo Action**:
1. Open second browser (or incognito) logged in as a student user
2. Click the same LTI activity link
3. Wait for redirect and show student dashboard

#### What's Happening Behind the Scenes

**Same LTI flow** (steps 1-2 repeat), but:
- JWT roles claim includes: `http://purl.imsglobal.org/vocab/lis/v2/institution/person#Learner`
- `determine_role()` sees no "Instructor"/"Administrator"/"TA" → returns "student"
- Redirect to `/pages/student-dashboard.html` instead of teacher dashboard
- User sees **only** assignments for their `course_id` and `resource_link_id`

---

### Step 6: Student Starts an Attempt (Spawns Docker Container)

#### What to Say Out Loud

> *"As a student, I can see the assignment I created. I click 'Start Attempt' and the system creates a fresh Docker container just for me with the starter code pre-loaded."*

**Demo Action**:
1. On student dashboard, click "Bash String Manipulation"
2. Click "Start Attempt"
3. Observe: Container ID appears, terminal loads below

#### What's Happening Behind the Scenes

**Endpoint**: `POST /api/attempts`

```python
def create_attempt():
    user = _require_student()  # Ensures role != 'teacher'
    payload = request.get_json()
    assignment_id = payload.get('assignment_id')
    
    user_sub = user['sub']
    resource_link_id = user['resource_link_id']
    
    # Verify student can access this assignment
    assignment = db.query(Assignment).filter_by(
        course_id=user['course_id'],
        resource_link_id=resource_link_id,
        assignment_id=assignment_id,
        is_configured=True
    ).first()
    if not assignment:
        return 404, {"error": "Assignment not found or not configured"}
    
    # Create Docker container
    container_info = create_attempt_container()  # Calls Docker API
    
    # Create Attempt record
    attempt = Attempt(
        user_sub=user_sub,
        resource_link_id=resource_link_id,
        container_id=container_info['container_id'],
        status='active'
    )
    db.add(attempt)
    db.commit()
    
    # Populate container with starter files
    populate_workspace_from_starter(
        container_id=attempt.container_id,
        starter_dir=assignment.starter_extracted_path
    )
    
    # Log event
    log_event('attempt.created', actor_sub=user_sub, ...)
    
    return 201, {"attempt_id": attempt.attempt_id, "container_id": container_id}
```

**Docker Container Creation** (`services/docker_service.py`):

```python
def create_attempt_container():
    client = docker.from_env()
    
    # Pull/use 'lti-shell-sandbox:latest' image
    container = client.containers.run(
        image='lti-shell-sandbox:latest',
        command=['/bin/bash', '-lc', 'sleep infinity'],  # Keep shell alive
        detach=True,
        
        # Network isolation
        network_disabled=True,  # NO external network access
        
        # Security constraints
        user='65532:65532',     # Non-root UID:GID
        cap_drop=['ALL'],       # Drop all Linux capabilities
        security_opt=['no-new-privileges:true'],  # Prevent privilege escalation
        
        # Resource limits
        mem_limit='256m',       # Hard memory limit
        nano_cpus=500_000_000,  # 0.5 CPU cores
        pids_limit=128,         # Max 128 processes (prevent fork bombs)
        
        # Temporary filesystems (RAM-backed, auto-delete on exit)
        tmpfs={
            '/tmp': 'rw,noexec,nosuid,size=64m,mode=1777',
            '/workspace': 'rw,exec,size=256m,uid=65532,gid=65532'
        },
        
        # Auto-cleanup
        auto_remove=True,       # Docker automatically removes container when it stops
        
        # Environment
        environment={
            'HOME': '/home/sandbox',
            'LANG': 'C.UTF-8',
            'TERM': 'xterm-256color'
        },
        working_dir='/workspace'
    )
    
    return {
        'container_id': container.id[:12],  # Use short ID
        'docker_status': container.status   # 'running'
    }

    # Populate workspace from starter
def populate_workspace_from_starter(container_id, starter_dir):
    client = docker.from_env()
    container = client.containers.get(container_id)
    
    # TAR starter files
    tar_bytes = _build_dir_tar_bytes(Path(starter_dir))
    
    # Copy into container using docker cp equivalent
    result = subprocess.run([
        'docker', 'cp', f'{starter_dir}/.', f'{container_id}:/workspace/'
    ], check=True)
```

**Security Model**:
```
Container = Sandbox
├── NO network (network_disabled=True)
├── NO privileged operations (cap_drop=['ALL'])
├── NO escalation (security_opt=['no-new-privileges:true'])
├── Resource-limited (256M memory, 0.5 CPU, 128 processes max)
├── Non-root user (uid 65532)
├── Temp filesystems (auto-delete, no persistence)
└── Auto-removed on exit (auto_remove=True)

Result: Even if student code has a security flaw, it cannot:
- ✗ Access network
- ✗ Escape container
- ✗ Consume unlimited resources
- ✗ Compromise host system
```

---

### Step 7: Student Interacts via Terminal (WebSocket)

#### What to Say Out Loud

> *"The terminal is now live. I can type Bash commands—they execute inside the container. Watch: I can see the starter files, modify them, and test my code."*

**Demo Action**:
1. Type: `ls -la`
2. Observe: Starter files listed
3. Type: `cat hello.sh`
4. Type: `echo "reverse() { ... }" >> hello.sh`
5. Type: `./hello.sh "test"`
6. Show output in real-time

#### What's Happening Behind the Scenes

**WebSocket Bridge** (`routes/terminal.py` → `/ws/terminal?attempt_id=...`):

```python
@sock.route('/ws/terminal')
def terminal_socket(ws):
    attempt_id = request.args.get('attempt_id')
    user = _require_user()
    attempt = _get_attempt_for_user(attempt_id)  # Validates access
    
    if not attempt.container_id:
        ws.send(json.dumps({"type": "error", "message": "No container"}))
        return
    
    client = docker.from_env()
    container = client.containers.get(attempt.container_id)
    
    # Message loop: receive from browser, execute in container, send back
    while True:
        try:
            message = ws.receive()  # Wait for WebSocket message
            if not message:
                break
            
            data = json.loads(message)
            
            if data.get('type') == 'input':
                # Execute command in container
                command = data.get('command', '')
                
                # Use docker exec to run in the already-running container
                result = container.exec_run(
                    ['/bin/bash', '-lc', command],
                    stdout=True,
                    stderr=True
                )
                
                # Send output back through WebSocket
                ws.send(json.dumps({
                    "type": "output",
                    "data": result.output.decode('utf-8', 'replace'),
                    "exit_code": result.exit_code
                }))
                
                # Update last activity timestamp (for expiration tracking)
                touch_attempt_activity(attempt_id)
                
        except Exception as exc:
            ws.send(json.dumps({"type": "error", "message": str(exc)}))
            break
```

**Detailed Flow**:
```
1. Browser: xterm.js captures key presses
   ↓
2. JavaScript sends: {"type": "input", "command": "ls -la"}
   ↓
3. WebSocket /ws/terminal receives message
   ↓
4. Backend: container.exec_run(['/bin/bash', '-lc', 'ls -la'])
   ↓
5. Docker daemon executes in container:
   - Forks bash process
   - Runs 'ls -la' inside /workspace
   - Captures stdout/stderr
   ↓
6. Backend sends back: {"type": "output", "data": "...", "exit_code": 0}
   ↓
7. Browser: xterm.js renders output to terminal
   ↓
8. User sees output in real-time
```

**Activity Tracking**:
```python
def touch_attempt_activity(attempt_id, now=None):
    """Update last_activity_at to reset expiration timer."""
    db.query(Attempt).filter_by(attempt_id=attempt_id).update({
        'last_activity_at': now or datetime.now(timezone.utc)
    })
    db.commit()
```

Every terminal command resets the inactivity timer. If student goes idle for 15+ minutes (configurable), the attempt is **auto-expired** and the container is destroyed.

---

## Part 4: SUBMISSION & GRADING - Demo Flow

### Step 8: Student Submits for Grading

#### What to Say Out Loud

> *"Once I'm satisfied with my solution, I click 'Submit for Grading'. The system will run my startup code against the test suite, extract the score, and show me feedback."*

**Demo Action**:
1. Click "Submit for Grading" button
2. Observe status change to "grading..."
3. Wait for result

#### What's Happening Behind the Scenes

**Endpoint**: `POST /api/attempts/<id>/submit`

```python
def submit_attempt(attempt_id):
    user = _require_student()
    attempt = _get_attempt_for_user(attempt_id)
    
    if attempt.status != 'active':
        return 400, {"error": "Attempt not active"}
    
    assignment = db.query(Assignment).get(attempt.assignment_id)
    
    # Create Submission record with initial status
    submission = Submission(
        assignment_id=attempt.assignment_id,
        attempt_id=attempt.attempt_id,
        user_sub=user['sub'],
        resource_link_id=user['resource_link_id'],
        status='grading',  # In-progress
        score=0.0,
        max_points=assignment.max_points
    )
    db.add(submission)
    db.commit()
    
    # Run grading in background (or sync for demo)
    try:
        result = run_grading_for_attempt(assignment, attempt)
        # result = {'status': 'passed'|'failed'|'timeout', 
        #           'score': 85.0, 'stdout': '...', 'stderr': '...'}
    except Exception as exc:
        submission.status = 'error'
        submission.feedback_stderr = str(exc)
        db.commit()
        return 500, {"error": str(exc)}
    
    # Update Submission with grading results
    submission.status = result['status']
    submission.score = result['score']
    submission.feedback_stdout = result['stdout']
    submission.feedback_stderr = result['stderr']
    submission.completed_at = datetime.now(timezone.utc)
    db.commit()
    
    # Attempt is now complete
    attempt.status = 'submitted'
    terminate_attempt_container(attempt.container_id)  # Stop container
    db.commit()
    
    # Log grading event
    log_event('submission.graded', actor_sub=user['sub'], ...)
    
    # Trigger grade passback to Moodle
    post_grade_async(submission)  # Background job or sync
    
    return 200, {"submission_id": submission.submission_id, "score": result['score']}
```

**Database State After Submit**:
```sql
-- Submission record
INSERT INTO submissions (...) VALUES (
  'sub_uuid_123', 'assign_uuid_abc', 'attempt_uuid_xyz',
  'student_sub_12345', 'activity_link_202',
  'passed', 85.5, 100.0, 'Test 1 PASS...', '', ...
);

-- Attempt record updated
UPDATE attempts SET status='submitted' WHERE attempt_id='attempt_uuid_xyz';
```

---

### Step 9: Grading Engine Runs Tests

#### What to Say Out Loud

> *"Behind the scenes, the grading engine is executing my test script in the student's container. Here's what it does:*
> 
> 1. *Injects the tests (run_tests.sh) into the container*
> 2. *Runs the test script, which executes the student's code*
> 3. *Captures stdout/stderr*
> 4. *Looks for a SCORE line in the output to extract the numeric score*
> 5. *Cleans up the container and terminates it"*

**Demo Action**: Show the test output/feedback to student

#### What's Happening Behind the Scenes

**Grading Service** (`services/grading_service.py`):

```python
def run_grading_for_attempt(assignment, attempt):
    """Execute tests inside student's container."""
    
    if not attempt.container_id:
        raise ValueError("Attempt has no container")
    
    if not assignment.tests_extracted_path:
        raise ValueError("Assignment has no tests")
    
    # 1. Load test files from disk
    tests_dir = Path(assignment.tests_extracted_path)
    
    # 2. TAR test files with prefix 'lti_tests/'
    tests_tar = _build_tests_tar_bytes(tests_dir)
    # Result: TAR contains lti_tests/run_tests.sh, lti_tests/test_data/*, etc.
    
    # 3. Stage tests inside container into /tmp/lti_tests/
    _stage_tests_in_container(attempt.container_id, tests_tar)
    # Runs: docker exec container bash -lc "tar -xf - -C /tmp"
    
    # 4. Execute run_tests.sh
    run_cmd = (
        "set -e; "
        "cd /tmp/lti_tests; "
        "RUNNER=$(find . -name run_tests.sh | head -1); "
        "chmod +x \"$RUNNER\"; "
        "cd /workspace; "  # Test runs in student's workspace
        f"timeout 30s bash \"/tmp/lti_tests/${{RUNNER#./}}\""
    )
    
    client = docker.from_env()
    container = client.containers.get(attempt.container_id)
    
    result = container.exec_run(
        ['/bin/bash', '-lc', run_cmd],
        demux=True,  # Separate stdout and stderr
        stdout=True,
        stderr=True
    )
    
    stdout_bytes, stderr_bytes = result.output
    stdout = stdout_bytes.decode('utf-8', 'replace')
    stderr = stderr_bytes.decode('utf-8', 'replace')
    exit_code = result.exit_code
    
    # 5. Determine test status based on exit code
    if exit_code == 124:
        status = 'timeout'      # timeout command returns 124
    elif exit_code == 0:
        status = 'passed'       # Test script exited cleanly
    else:
        status = 'failed'       # Non-zero exit
    
    # 6. Extract SCORE from output
    score = _extract_score(stdout, stderr, max_points=100.0, passed=(status == 'passed'))
    
    return {
        'status': status,       # 'passed', 'failed', or 'timeout'
        'score': score,         # Extracted from "SCORE=85.5"
        'stdout': stdout,       # Full test output for student feedback
        'stderr': stderr,       # Any error messages
        'exit_code': exit_code  # Raw exit code
    }
```

**Score Extraction Logic**:

```python
SCORE_PATTERN = re.compile(r'SCORE\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)', re.IGNORECASE)

def _extract_score(stdout, stderr, max_points, passed):
    """Find SCORE= in output; clamp to [0, max_points]."""
    combined = stdout + '\n' + stderr
    match = SCORE_PATTERN.search(combined)
    
    if match:
        # Explicit score found
        score = float(match.group(1))
        return max(0.0, min(score, max_points))  # Clamp to [0, max]
    
    # No explicit score; use exit code
    if passed:
        return float(max_points)  # Full credit
    else:
        return 0.0  # No credit
```

**Example Test Script** (`run_tests.sh`):

```bash
#!/bin/bash
# This is written by the TEACHER

# Test: Does hello.sh exist and is it executable?
if [ ! -x hello.sh ]; then
    echo "hello.sh not found or not executable"
    SCORE=0
    exit 1
fi

# Test 1: Reverse "hello" → should produce "olleh"
result=$(./hello.sh reverse "hello")
if [ "$result" = "olleh" ]; then
    echo "Test 1 PASSED"
    score1=25
else
    echo "Test 1 FAILED: got '$result', expected 'olleh'"
    score1=0
fi

# Test 2: Uppercase "hello" → "HELLO"
result=$(./hello.sh upper "hello")
if [ "$result" = "HELLO" ]; then
    echo "Test 2 PASSED"
    score2=25
else
    echo "Test 2 FAILED"
    score2=0
fi

# ... more tests ...

total=$((score1 + score2 + score3 + score4))
echo "SCORE=$total"
exit 0
```

**Grading Output**:
```
Test 1 PASSED
Test 2 PASSED
Test 3 FAILED
Test 4 PASSED
SCORE=75
```

---

### Step 10: Grade Passback to Moodle (AGS - Assignment and Grade Services)

#### What to Say Out Loud

> *"Once grading is complete, the system automatically sends the grade back to Moodle using the LTI AGS (Assignment and Grade Services) standard. The student's score appears in the Moodle gradebook within seconds."*

**Demo Action**:
1. In student browser: Observe "Grade: 75/100" ✓
2. Switch to teacher browser → Click "Gradebook"
3. Show student's score: 75/100 appears in the grid

#### What's Happening Behind the Scenes

**Grade Passback Flow** (`services/lti_ags_service.py`):

```python
def post_grade_with_retry(
    launch_id,
    user_sub,
    score,
    max_points,
    lineitem_url,
    max_attempts=3
):
    """Send grade to Moodle via LTI AGS with automatic retry."""
    
    for attempt in range(1, max_attempts + 1):
        try:
            # 1. Retrieve cached launch data using launch_id
            #    (Cached during LTI login at router level)
            message_launch = _get_message_launch_from_cache(launch_id)
            
            # 2. Verify Moodle included AGS endpoint
            if not message_launch.has_ags():
                raise ValueError("Launch does not include AGS")
            
            ags = message_launch.get_ags()
            
            # 3. Verify permissions
            if not ags.can_put_grade():
                raise ValueError("AGS scopes don't allow grade writing")
            
            # 4. Build Grade object per LTI spec
            grade = Grade()
            grade.set_score_given(float(score))      # Student's score
            grade.set_score_maximum(float(max_points))  # Total points
            grade.set_user_id(user_sub)              # Unique student ID
            grade.set_timestamp(datetime.now(timezone.utc).isoformat())
            grade.set_activity_progress('Completed')
            grade.set_grading_progress('FullyGraded')
            
            # 5. Create LineItem (points configuration)
            lineitem = LineItem().set_id(lineitem_url)
            
            # 6. POST grade to Moodle
            #    PUT https://moodle.../ags/lineitem/1/scores
            response = ags.put_grade(grade, lineitem=lineitem)
            
            # Success!
            return {
                'success': True,
                'attempts': attempt,
                'error': ''
            }
            
        except Exception as exc:
            last_error = str(exc)
            if attempt < max_attempts:
                time.sleep(1.0 * attempt)  # Exponential backoff
    
    # Exhausted retries
    return {
        'success': False,
        'attempts': max_attempts,
        'error': last_error
    }
```

**What AGS Does** (Under the Hood):

```
Behind the scenes in Moodle:

1. Moodle receives PUT /ags/lineitem/1/scores
   Body: {
     "scoreGiven": 75,
     "scoreMaximum": 100,
     "userId": "student_sub_12345",
     "activityProgress": "Completed"
   }

2. Moodle validates:
   - Is this a valid lineitem for this user?
   - Does the JWT have permission (score:put scope)?
   - Is the user enrolled in the course?

3. Moodle updates gradebook:
   UPDATE grades SET score=75, graded_at=NOW() WHERE user_id=... AND lineitem_id=1

4. Moodle sends notification to student:
   "Your grade for 'Bash String Manipulation' is now available"

5. Teacher sees updated gradebook immediately
   (or after refresh)
```

**Security Model**:
- ✓ JWT signature validates the request came from LTI-Shell
- ✓ Scope validation ensures only grade writing is allowed
- ✓ Token expires quickly (~5 min) to limit replay window
- ✓ HTTPS encryption in transit

---

## Part 5: COMPLETE AUDIT TRAIL

#### What to Say Out Loud

> *"Throughout this entire flow, every action has been logged for compliance and debugging. Let me query the audit log to show what happened."*

**Demo Action**: Query audit logs (if database is accessible)

#### What's Happening Behind the Scenes

**Audit Events Logged**:

```python
# 1. LTI Launch
log_event(
    'lti.launch.validated',
    actor_sub='student_sub_12345',
    resource_link_id='activity_link_202',
    details={'role': 'student', 'course_id': 'course_89101'}
)

# 2. Attempt Created
log_event(
    'attempt.created',
    actor_sub='student_sub_12345',
    resource_link_id='activity_link_202',
    details={'assignment_id': 'assign_abc', 'container_id': 'con_xyz'}
)

# 3. Submission Graded
log_event(
    'submission.graded',
    actor_sub='system',  # Grading is automatic
    resource_link_id='activity_link_202',
    details={
        'assignment_id': 'assign_abc',
        'submission_id': 'sub_123',
        'score': 75.0,
        'status': 'passed'
    }
)

# 4. Grade Passback
log_event(
    'grade.passback.succeeded',
    actor_sub='system',
    resource_link_id='activity_link_202',
    details={
        'user_sub': 'student_sub_12345',
        'score': 75.0,
        'lineitem_url': '...'
    }
)
```

**Audit Log Schema** (`audit_logs` table):

```sql
Table: audit_logs
─────────────────────────────────────────────────────
id INT PRIMARY KEY auto_increment
event_type VARCHAR(128)                -- 'lti.launch.validated', 'attempt.created', ...
actor_sub VARCHAR(255)                 -- Who took the action
resource_link_id VARCHAR(255)          -- Which LTI activity
details_json TEXT                      -- {"key": "value", ...}
created_at DATETIME WITH TIMEZONE      -- When it happened
```

**Example Query**:
```sql
SELECT * FROM audit_logs
WHERE resource_link_id = 'activity_link_202'
ORDER BY created_at DESC
LIMIT 20;

Result:
────────────────────────────────────────────────────
event_type: grade.passback.succeeded
actor_sub: system
created_at: 2026-04-27 14:32:10 UTC
details: {"score": 75, "user_sub": "student_sub_12345"}

event_type: submission.graded
actor_sub: system
created_at: 2026-04-27 14:32:05 UTC
details: {"score": 75, "status": "passed"}

event_type: attempt.created
actor_sub: student_sub_12345
created_at: 2026-04-27 14:29:15 UTC
details: {"container_id": "con_xyz", "assignment_id": "assign_abc"}

event_type: lti.launch.validated
actor_sub: student_sub_12345
created_at: 2026-04-27 14:28:00 UTC
details: {"role": "student", "course_id": "course_89101"}
```

---

## Summary: 10-Minute Talk Track

### Minute 1-2: Introduction
> "LTI-Shell is a Bash sandbox integrated into Moodle. It combines three paradigms:
> 1. **Learning Tools Interoperability (LTI 1.3)**: Secure authentication between Moodle and external tools
> 2. **Docker Sandboxing**: Isolated, resource-limited containers for code execution
> 3. **Automated Grading**: Script-based assessment with instant feedback
> 
> Today I'll show the complete flow: teacher creates assignment → student solves it → automated grading → grade appears in Moodle."

### Minute 2-3: Teacher Workflow
> "First, a teacher creates an assignment. The LTI handshake authenticates them, assigns their role, and directs them to the teacher dashboard. They create an assignment, upload starter code and tests."

*[Demo: Create assignment, upload ZIPs]*

### Minute 3-5: Student Workflow & Terminal
> "Students see the assignment, click 'Start Attempt', and get a Docker container with the starter code. They interact with it via terminal—typing Bash commands that execute inside the sandbox."

*[Demo: Type commands, edit code]*

### Minute 5-8: Grading
> "When the student submits, the system injects the test script, runs it, extracts the score, and terminates the container. Within seconds, the grade appears in Moodle's gradebook using LTI AGS."

*[Demo: Submit, watch grading, show result in Moodle]*

### Minute 8-10: Security & Architecture
> "Security is baked in at every layer: LTI uses JWT cryptography, Docker containers run as non-root with no network access and resource limits, and every action is logged for compliance. This ensures that even if student code has a vulnerability, it cannot escape the sandbox or compromise the system."

*[Optional: Show audit logs, discuss architecture diagram]*

---

## Key Technical Concepts to Highlight

| Concept | Why It Matters |
|---------|---|
| **LTI 1.3 OIDC** | No stored passwords; Moodle handles auth; JWT secures flow |
| **Role Detection** | Same login URL, different dashboards (teacher vs. student) |
| **Docker Sandbox** | Code isolation; resource limits prevent DoS; auto-cleanup |
| **WebSocket Terminal** | Real-time command execution; activity tracking resets timeout |
| **Grading Service** | Automated with customizable test scripts; score extraction via regex |
| **LTI AGS** | Grades automatically appear in Moodle without manual copy-paste |
| **Audit Logging** | Complete trail for compliance, debugging, analytics |

---

## Troubleshooting Common Demo Issues

| Issue | Solution |
|-------|----------|
| Docker image not found | Pre-build: `docker build -t lti-shell-sandbox:latest -f docker/sandbox/Dockerfile .` |
| LTI launch fails | Verify LTI config (lti.json) matches Moodle's tool config |
| Terminal doesn't load | Check Docker daemon is running; check WebSocket firewall rules |
| Grade doesn't passback | Check network connectivity to Moodle; verify AGS scopes in JWT |
| Slow grading | Check Docker resource limits; might need to tune CPU/memory |

---

## Pre-Demo Checklist

- [ ] Moodle instance running and LTI-Shell configured as external tool
- [ ] Flask backend running: `.venv\Scripts\python app.py`
- [ ] Docker daemon running: `docker ps` works
- [ ] Sandbox image built: `docker build -t lti-shell-sandbox:latest -f docker/sandbox/Dockerfile .`
- [ ] Database initialized: SQLite created and schema exists
- [ ] Two Moodle user accounts: one teacher, one student
- [ ] Assignment already created and configured (or demo creating one live)
- [ ] Network connectivity from browser to Flask backend
- [ ] HTTPS certificates valid (or demo on localhost)

---

## Questions for Q&A

**"Why Docker?"**
> Containers are lightweight, fast to spin up/tear down, and provide strong isolation compared to VMs. A sandbox container starts in <1 second.

**"How do you prevent resource exhaustion?"**
> Memory, CPU, and process limits at container creation time. Even a fork bomb can only spawn 128 processes before hitting the limit.

**"What if a student writes malicious code?"**
>The container has no network, runs as non-root, and can't execute code outside its filesystem. Even `sudo` is blocked.

**"Can students see each other's code?"**
> No—each attempt gets its own isolated container. There's no shared storage between students.

**"What happens if a test times out?"**
> The grading service has a 30-second timeout. If exceeded, the exit code is 124, and the score defaults gracefully (usually 0).

**"How does it scale?"**
> Each student attempt is a separate container, so horizontal scaling is straightforward: just add more Docker nodes.
