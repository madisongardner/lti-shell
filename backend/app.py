import os
from flask import Flask, session, jsonify, redirect
from extensions import cache, sess
from config import Config
from database import init_db
from flask_sock import Sock
from services.attempt_cleanup_service import start_attempt_cleanup_worker

# create flask app

app = Flask(
    __name__,
    static_folder='../frontend',
    static_url_path='',
)
sock = Sock(app)
app.config.from_object(Config)

# init extentions
cache.init_app(app)
sess.init_app(app)

# Import and register the LTI blueprint

from routes.lti import lti_bp
from routes.assignments import assignments_bp
from routes.terminal import register_terminal_socket

app.register_blueprint(lti_bp, url_prefix='/lti')
app.register_blueprint(assignments_bp, url_prefix='/api')
register_terminal_socket(sock)

with app.app_context():
    init_db()

@app.route('/')
def index():
    """Root route - redirect based on session if logged in, else show index"""
    if 'user' in session:
        role = session['user'].get('role', 'student')
        if role == 'teacher':
            return redirect('/pages/teacher-dashboard.html')
        return redirect('/pages/student-dashboard.html')
    return app.send_static_file('index.html')


@app.route('/api/user-info')
def user_info():
    """API endpoint for frontend to get current user info from session"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify(session['user'])

if __name__ == '__main__':
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_attempt_cleanup_worker()
    app.run(host='0.0.0.0', port=5000, debug=True)
