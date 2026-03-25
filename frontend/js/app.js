function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;

}

function setAssignmentMessage(message, isError = false) {
    const el = document.getElementById('assignment-message');
    if (!el) return;
    el.style.color = isError ? 'red' : '#2c3e50';
    el.textContent = message || '';
}

function toIsoFromLocalDatetime(value) {
    if (!value) return null;
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return null;
    return dt.toISOString();
}

function toLocalDatetimeInputValue(isoValue) {
    if (!isoValue) return '';
    const dt = new Date(isoValue);
    if (Number.isNaN(dt.getTime())) return '';
    const offsetMs = dt.getTimezoneOffset() * 60000;
    return new Date(dt.getTime() - offsetMs).toISOString().slice(0, 16);
}

function formatDateDisplay(isoValue) {
    if (!isoValue) return '-';
    const dt = new Date(isoValue);
    if (Number.isNaN(dt.getTime())) return '-';
    return dt.toLocaleString();
}

function wireTeacherAssignmentManager(user) {
    const form = document.getElementById('assignment-form');
    const updateBtn = document.getElementById('assignment-update');
    const empty = document.getElementById('assignments-empty');
    const table = document.getElementById('assignments-table');
    const tbody = document.getElementById('assignments-tbody');

    if (!form || !updateBtn || !empty || !table || !tbody) return;

    let selectedAssignmentId = null;

    const titleInput = document.getElementById('assignment-title');
    const instructionsInput = document.getElementById('assignment-instructions');
    const dueAtInput = document.getElementById('assignment-due-at');
    const maxPointsInput = document.getElementById('assignment-max-points');
    const starterZipInput = document.getElementById('starter-zip');
    const testsZipInput = document.getElementById('tests-zip');
    const starterUploadBtn = document.getElementById('starter-upload-btn');
    const testsUploadBtn = document.getElementById('tests-upload-btn');
    const artifactStatusEl = document.getElementById('artifact-status');

    const resetSelection = () => {
        selectedAssignmentId = null;
        updateBtn.disabled = true;
        if (starterUploadBtn) starterUploadBtn.disabled = true;
        if (testsUploadBtn) testsUploadBtn.disabled = true;
        if (artifactStatusEl) artifactStatusEl.textContent = 'Select an assignment to view artifact status.';
    };

    const fillForm = (assignment) => {
        titleInput.value = assignment.title || '';
        instructionsInput.value = assignment.instructions || '';
        dueAtInput.value = toLocalDatetimeInputValue(assignment.due_at);
        maxPointsInput.value = assignment.max_points || 100;
    };

    const buildPayloadFromForm = () => ({
        title: titleInput.value,
        instructions: instructionsInput.value,
        due_at: toIsoFromLocalDatetime(dueAtInput.value),
        max_points: Number(maxPointsInput.value),
    });

    const renderArtifactStatus = (status) => {
        if (!artifactStatusEl) return;
        if (!status) {
            artifactStatusEl.textContent = '';
            return;
        }

        const reasons = Array.isArray(status.configuration_reasons) ? status.configuration_reasons : [];
        artifactStatusEl.innerHTML =
            '<strong>Readiness:</strong> ' + (status.is_configured ? 'Ready' : 'Not ready') + '<br>' +
            '<strong>Starter ZIP:</strong> ' + (status.starter_zip_uploaded ? 'Uploaded' : 'Missing') + '<br>' +
            '<strong>Tests ZIP:</strong> ' + (status.tests_zip_uploaded ? 'Uploaded' : 'Missing') + '<br>' +
            '<strong>run_tests.sh:</strong> ' + (status.has_required_test_runner ? 'Present' : 'Missing') + '<br>' +
            '<strong>Artifacts Validated:</strong> ' + (status.artifacts_validated ? 'Yes' : 'No') +
            (status.artifact_validation_error ? ('<br><strong>Last Validation Error:</strong> ' + escapeHtml(status.artifact_validation_error)) : '') +
            (reasons.length ? ('<br><strong>Missing Requirements:</strong> ' + escapeHtml(reasons.join('; '))) : '');
    };

    const refreshArtifactStatus = async () => {
        if (!selectedAssignmentId) {
            renderArtifactStatus(null);
            return;
        }
        try {
            const status = await API.getAssignmentArtifactsStatus(selectedAssignmentId);
            renderArtifactStatus(status);
        } catch (error) {
            setAssignmentMessage(error.message || 'Failed to load artifact status.', true);
        }
    };

    const loadAssignments = async () => {
        try {
            const data = await API.listAssignments();
            const items = data.items || [];

            if (!items.length) {
                empty.style.display = 'block';
                table.style.display = 'none';
                tbody.innerHTML = '';
                return;
            }

            empty.style.display = 'none';
            table.style.display = 'table';
            tbody.innerHTML = items.map((item) => (
                '<tr data-assignment-id="' + escapeHtml(item.assignment_id) + '">' +
                '<td>' + escapeHtml(item.title) + '</td>' +
                '<td>' + escapeHtml(item.resource_link_id) + '</td>' +
                '<td>' + escapeHtml(formatDateDisplay(item.due_at)) + '</td>' +
                '<td>' + escapeHtml(String(item.max_points)) + '</td>' +
                '<td>' + escapeHtml(item.is_configured ? 'Yes' : 'No') + '</td>' +
                '</tr>'
            )).join('');

            const rows = Array.from(tbody.querySelectorAll('tr'));
            rows.forEach((row) => {
                row.style.cursor = 'pointer';
                row.addEventListener('click', () => {
                    const assignmentId = row.getAttribute('data-assignment-id');
                    const assignment = items.find((item) => item.assignment_id === assignmentId);
                    if (!assignment) return;

                    rows.forEach((r) => {
                        r.style.backgroundColor = '';
                    });
                    row.style.backgroundColor = '#eef6ff';
                    selectedAssignmentId = assignment.assignment_id;
                    updateBtn.disabled = false;
                    if (starterUploadBtn) starterUploadBtn.disabled = false;
                    if (testsUploadBtn) testsUploadBtn.disabled = false;
                    fillForm(assignment);
                    setAssignmentMessage('Selected assignment ' + assignment.assignment_id + ' for editing.');
                    refreshArtifactStatus();
                });
            });
        } catch (error) {
            setAssignmentMessage(error.message || 'Failed to load assignments.', true);
        }
    };

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        try {
            const payload = buildPayloadFromForm();
            await API.createAssignment(payload);
            setAssignmentMessage('Assignment created for activity ' + (user.resource_link_title || user.resource_link_id) + '.');
            resetSelection();
            await loadAssignments();
        } catch (error) {
            setAssignmentMessage(error.message || 'Failed to create assignment.', true);
        }
    });

    updateBtn.addEventListener('click', async () => {
        if (!selectedAssignmentId) return;
        try {
            const payload = buildPayloadFromForm();
            await API.updateAssignment(selectedAssignmentId, payload);
            setAssignmentMessage('Assignment updated.');
            await loadAssignments();
            await refreshArtifactStatus();
        } catch (error) {
            setAssignmentMessage(error.message || 'Failed to update assignment.', true);
        }
    });

    if (starterUploadBtn) {
        starterUploadBtn.addEventListener('click', async () => {
            if (!selectedAssignmentId) return;
            if (!starterZipInput || !starterZipInput.files || !starterZipInput.files[0]) {
                setAssignmentMessage('Choose a starter ZIP file first.', true);
                return;
            }
            try {
                await API.uploadStarterZip(selectedAssignmentId, starterZipInput.files[0]);
                setAssignmentMessage('Starter ZIP uploaded and validated.');
                await loadAssignments();
                await refreshArtifactStatus();
            } catch (error) {
                setAssignmentMessage(error.message || 'Failed to upload starter ZIP.', true);
                await refreshArtifactStatus();
            }
        });
    }

    if (testsUploadBtn) {
        testsUploadBtn.addEventListener('click', async () => {
            if (!selectedAssignmentId) return;
            if (!testsZipInput || !testsZipInput.files || !testsZipInput.files[0]) {
                setAssignmentMessage('Choose a tests ZIP file first.', true);
                return;
            }
            try {
                await API.uploadTestsZip(selectedAssignmentId, testsZipInput.files[0]);
                setAssignmentMessage('Tests ZIP uploaded and validated.');
                await loadAssignments();
                await refreshArtifactStatus();
            } catch (error) {
                setAssignmentMessage(error.message || 'Failed to upload tests ZIP.', true);
                await refreshArtifactStatus();
            }
        });
    }

    resetSelection();
    loadAssignments();
}

document.addEventListener('DOMContentLoaded', async () => {
    const userInfoDiv = document.getElementById('user-info');
    const userInfo = document.getElementById('error');

    const user = await API.getUserInfo();
    if(!user) {
        userInfoDiv.innerHTML = '';
        userInfo.style.display = 'block';
        userInfo.textContent = 'Not authenticated. Please log in through your LMS.';
        return;

    }

    userInfoDiv.innerHTML =
        '<table>' +
        '<tr><th>Name</th><td>' + escapeHtml(user.name) + '</td></tr>' +
        '<tr><th>Email</th><td>' + escapeHtml(user.email) + '</td></tr>' +
        '<tr><th>Role</th><td>' + escapeHtml(user.role) + '</td></tr>' +
        '<tr><th>Course</th><td>' + escapeHtml(user.course_title) + ' (' + escapeHtml(user.course_label) + ')</td></tr>' +
        '<tr><th>Activity</th><td>' + escapeHtml(user.resource_link_title) + '</td></tr>' +
        '</table>';

    if (user.role === 'teacher') {
        wireTeacherAssignmentManager(user);
    }
});