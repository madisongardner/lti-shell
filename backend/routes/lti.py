import os
import pprint

from flask import Blueprint, request, session, jsonify, redirect, current_app
from pylti1p3.contrib.flask import (
    FlaskOIDCLogin,
    FlaskMessageLaunch,
    FlaskRequest,
    FlaskCacheDataStorage


)
from pylti1p3.tool_config import ToolConfJsonFile
from services.lti_service import extract_user_data

lti_bp = Blueprint('lti', __name__)


def get_tool_conf():
    """Load LTI tool configuration from the JSON file."""
    config_file = current_app.config['LTI_CONFIG_FILE']
    return ToolConfJsonFile(config_file)


def get_launch_data_storage():
    """Get Cache storage that bridges the login and launch requests."""
    from extensions import cache
    return FlaskCacheDataStorage(cache)

# _____________________________
# Endpoint 1: OIDC Login Initiation
# _____________________________
@lti_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Moodle sends the user here first with: iss, login_hint, target_link_uri, lti_message_hint
    We redirect to the browser back to Moodle's auth endpoint 
    """
    tool_conf = get_tool_conf()
    launch_data_storage = get_launch_data_storage()

    flask_request = FlaskRequest()
    target_link_uri = flask_request.get_param('target_link_uri')
    if not target_link_uri:
        raise Exception('Missing "target_link_uri" param')
    
    oidc_login = FlaskOIDCLogin(
        flask_request,
        tool_conf,
        launch_data_storage=launch_data_storage,
    )
    
    return oidc_login \
        .enable_check_cookies() \
        .redirect(target_link_uri)


#_____________________________
# Endpoint 2: LTI Launch (JWT validation)
#_____________________________
@lti_bp.route('/launch', methods=['POST'])
def launch():
    """
    Moodle POSTs the signed JWT here. The libary validates it, 
    wer extract user info, store it in the session, and redirect
    to the current dashboard
    
    """
    tool_conf = get_tool_conf()
    launch_data_storage = get_launch_data_storage()

    message_launch = FlaskMessageLaunch(
        FlaskRequest(),
        tool_conf,
        launch_data_storage=launch_data_storage,
    )

    # This triggers JWT validation and will raise an exception if the launch is invalid
    launch_data = message_launch.get_launch_data()

    # Print the full launch data to the console for debugging
    pprint.pprint(launch_data)

    # Use our service to extract a clean user dict
    session['user'] = extract_user_data(launch_data, message_launch.get_launch_id())

    # Redirect based on role
    if session['user']['role'] == 'teacher':
        return redirect('/pages/teacher-dashboard.html')
    return redirect('/pages/student-dashboard.html')



#________________
# Endpoint 3: JWKS (JSON Web Key Set)
#_________________

@lti_bp.route('/jwks', methods=['GET'])
def jwks():
    """
    Exposes our public kets so Moodle can verify JWTs we sign."""

    tool_conf = get_tool_conf()
    return jsonify({'keys': tool_conf.get_jwks()})