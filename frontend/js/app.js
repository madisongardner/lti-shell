function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;

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
});