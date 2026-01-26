# agentic/api_utils.py
# =============================================================================
# CONSOLIDATED API UTILITIES
# =============================================================================
#
# This module consolidates common API utilities that were previously
# duplicated across multiple API modules:
#   - api_response() function
#   - handle_errors() decorator
#
# Previously duplicated in:
#   - agentic/api.py
#   - agentic/session_api.py
#   - agentic/strategy_rag/strategy_admin_api.py
#   - tools_api.py
#
# Usage:
#   from agentic.api_utils import api_response, handle_errors
#
#   @app.route('/endpoint')
#   @handle_errors
#   def my_endpoint():
#       return api_response(True, data={'key': 'value'})
#
# =============================================================================

import logging
from functools import wraps
from typing import Any, Optional, Dict
from flask import jsonify

logger = logging.getLogger(__name__)


def api_response(
    success: bool,
    data: Any = None,
    error: Optional[str] = None,
    status_code: int = 200,
    tags: Any = None,
    **extra_fields
) -> tuple:
    """
    Create a standardized API response.

    Provides consistent response format across all API endpoints:
    {
        "success": bool,
        "data": any,
        "error": string | null,
        "tags": object | null  (optional)
    }

    Args:
        success: Whether the request was successful
        data: Response data (any JSON-serializable type)
        error: Error message (if any)
        status_code: HTTP status code (default 200)
        tags: Optional tags object for frontend routing/UI hints
        **extra_fields: Additional fields to include in response

    Returns:
        Tuple of (Flask JSON response, status_code)

    Examples:
        # Success response
        return api_response(True, data={'user': user_dict})

        # Error response
        return api_response(False, error="User not found", status_code=404)

        # With tags (for frontend routing)
        return api_response(True, data=result, tags=response_tags)

        # With extra fields
        return api_response(True, data=result, message="Operation completed")
    """
    response = {
        "success": success,
        "data": data,
        "error": error
    }

    # Add tags if provided (backward compatible)
    if tags is not None:
        # Handle both dict and object with .dict() method
        if hasattr(tags, 'dict'):
            response["tags"] = tags.dict()
        elif hasattr(tags, 'model_dump'):
            response["tags"] = tags.model_dump()
        else:
            response["tags"] = tags

    # Add any extra fields
    response.update(extra_fields)

    return jsonify(response), status_code


def handle_errors(func=None, *, log_prefix: str = "API"):
    """
    Decorator for standardized error handling in API endpoints.

    Catches all exceptions, logs them with full traceback,
    and returns a standardized error response.

    Can be used with or without arguments:
        @handle_errors
        def endpoint(): ...

        @handle_errors(log_prefix="Session API")
        def session_endpoint(): ...

    Args:
        func: The view function to wrap (when used without parentheses)
        log_prefix: Prefix for log messages (default "API")

    Returns:
        Wrapped function with error handling

    Example:
        @app.route('/api/data')
        @handle_errors
        def get_data():
            # If this raises, returns {"success": false, "error": "..."}, 500
            return api_response(True, data=fetch_data())

        @app.route('/api/session')
        @handle_errors(log_prefix="Session API")
        def session_endpoint():
            return api_response(True, data=session_data())
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"{log_prefix} Error in {f.__name__}: {e}", exc_info=True)
                return api_response(
                    success=False,
                    error=str(e),
                    status_code=500
                )
        return decorated_function

    # Handle both @handle_errors and @handle_errors(...)
    if func is not None:
        return decorator(func)
    return decorator


def validate_request_json(required_fields: list = None, optional_fields: list = None):
    """
    Decorator to validate JSON request body.

    Checks that request has JSON body and required fields are present.

    Args:
        required_fields: List of required field names
        optional_fields: List of optional field names (for documentation)

    Returns:
        Decorator function

    Example:
        @app.route('/api/user', methods=['POST'])
        @validate_request_json(required_fields=['name', 'email'])
        def create_user():
            data = request.get_json()
            # data is guaranteed to have 'name' and 'email'
    """
    from flask import request

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()

            if not data:
                return api_response(
                    success=False,
                    error="Request body is required",
                    status_code=400
                )

            if required_fields:
                missing = [field for field in required_fields if not data.get(field)]
                if missing:
                    return api_response(
                        success=False,
                        error=f"Missing required fields: {', '.join(missing)}",
                        status_code=400
                    )

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_query_params(required_params: list = None):
    """
    Decorator to validate query parameters.

    Args:
        required_params: List of required query parameter names

    Returns:
        Decorator function

    Example:
        @app.route('/api/search')
        @validate_query_params(required_params=['q'])
        def search():
            query = request.args.get('q')
            # query is guaranteed to exist
    """
    from flask import request

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if required_params:
                missing = [param for param in required_params if not request.args.get(param)]
                if missing:
                    return api_response(
                        success=False,
                        error=f"Missing required query parameters: {', '.join(missing)}",
                        status_code=400
                    )

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'api_response',
    'handle_errors',
    'validate_request_json',
    'validate_query_params'
]
