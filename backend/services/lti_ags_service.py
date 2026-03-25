"""LTI AGS grade passback helpers with retry handling."""

import time
from datetime import datetime, timezone

from flask import current_app
from pylti1p3.contrib.flask import FlaskCacheDataStorage, FlaskMessageLaunch, FlaskRequest
from pylti1p3.grade import Grade
from pylti1p3.lineitem import LineItem
from pylti1p3.tool_config import ToolConfJsonFile

PASSBACK_MAX_ATTEMPTS = 3
PASSBACK_RETRY_DELAY_SECONDS = 1.0


def _get_message_launch_from_cache(launch_id: str):
    if not launch_id:
        raise ValueError("Missing launch_id required for AGS passback")

    tool_conf = ToolConfJsonFile(current_app.config["LTI_CONFIG_FILE"])
    from extensions import cache

    launch_data_storage = FlaskCacheDataStorage(cache)
    message_launch = FlaskMessageLaunch.from_cache(
        launch_id,
        FlaskRequest(),
        tool_conf,
        launch_data_storage=launch_data_storage,
    )
    return message_launch


def _build_grade(score: float, max_points: float, user_sub: str, comment: str = "") -> Grade:
    grade = Grade()
    grade.set_score_given(float(score))
    grade.set_score_maximum(float(max_points))
    grade.set_user_id(user_sub)
    grade.set_timestamp(datetime.now(timezone.utc).isoformat())
    grade.set_activity_progress("Completed")
    grade.set_grading_progress("FullyGraded")
    if comment:
        grade.set_comment(comment)
    return grade


def post_grade_with_retry(
    launch_id: str,
    user_sub: str,
    score: float,
    max_points: float,
    lineitem_url: str = "",
    max_attempts: int = PASSBACK_MAX_ATTEMPTS,
):
    """Post grade through LTI AGS with small retry budget.

    Returns a dict:
    {
      success: bool,
      attempts: int,
      error: str,
      response_body: object,
      response_headers: object,
    }
    """
    last_error = ""
    response_body = None
    response_headers = None

    for attempt in range(1, max_attempts + 1):
        try:
            message_launch = _get_message_launch_from_cache(launch_id)
            if not message_launch.has_ags():
                raise ValueError("Launch does not include AGS service")

            ags = message_launch.get_ags()
            if not ags.can_put_grade():
                raise ValueError("Launch AGS scopes do not allow score passback")

            grade = _build_grade(score, max_points, user_sub)

            lineitem = None
            if lineitem_url:
                lineitem = LineItem().set_id(lineitem_url)

            response = ags.put_grade(grade, lineitem=lineitem)
            response_body = response.get("body") if isinstance(response, dict) else None
            response_headers = response.get("headers") if isinstance(response, dict) else None
            return {
                "success": True,
                "attempts": attempt,
                "error": "",
                "response_body": response_body,
                "response_headers": response_headers,
            }
        except Exception as exc:
            last_error = str(exc)
            if attempt < max_attempts:
                time.sleep(PASSBACK_RETRY_DELAY_SECONDS * attempt)

    return {
        "success": False,
        "attempts": max_attempts,
        "error": last_error or "Unknown AGS passback error",
        "response_body": response_body,
        "response_headers": response_headers,
    }
