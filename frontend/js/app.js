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

    const resetSelection = () => {
        selectedAssignmentId = null;
        updateBtn.disabled = true;
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
                    fillForm(assignment);
                    setAssignmentMessage('Selected assignment ' + assignment.assignment_id + ' for editing.');
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
        } catch (error) {
            setAssignmentMessage(error.message || 'Failed to update assignment.', true);
        }
    });

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