# LTI 1.3 Claim URIs (constants)
ROLES_CLAIM = 'https://purl.imsglobal.org/spec/lti/claim/roles'
CONTEXT_CLAIM = 'https://purl.imsglobal.org/spec/lti/claim/context'
RESOURCE_LINK_CLAIM = 'https://purl.imsglobal.org/spec/lti/claim/resource_link'

# Role substrings that indicate instructor-level access
INSTRUCTOR_ROLES = ('Instructor', 'Administrator', 'TeachingAssistant')


def determine_role(roles_list):
    """
    Given a list of LTI role URIs, return 'teacher' or 'student'.
    """
    for role_uri in roles_list:
        if any(instructor_role in role_uri for instructor_role in INSTRUCTOR_ROLES):
            return 'teacher'
    return 'student'


def extract_user_data(launch_data, launch_id):
    """
    Extract a normalized user dict from raw LTI launch data.
    """
    roles_claim = launch_data.get(ROLES_CLAIM, [])
    context = launch_data.get(CONTEXT_CLAIM, {})
    resource_link = launch_data.get(RESOURCE_LINK_CLAIM, {})

    return {
        'name': launch_data.get('name', 'Unknown User'),
        'email': launch_data.get('email', ''),
        'sub': launch_data.get('sub', ''),
        'role': determine_role(roles_claim),
        'roles_raw': roles_claim,
        'course_id': context.get('id', ''),
        'course_title': context.get('title', ''),
        'course_label': context.get('label', ''),
        'resource_link_id': resource_link.get('id', ''),
        'resource_link_title': resource_link.get('title', ''),
        'launch_id': launch_id
    }
