from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Standardize all DRF error responses to:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable summary",
            "details": { ...field errors or context... }
        }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, 'default_code', 'ERROR')
        if hasattr(error_code, 'upper'):
            error_code = str(error_code).upper()
        else:
            error_code = 'ERROR'

        # Determine human-friendly message
        if isinstance(response.data, dict) and 'detail' in response.data:
            message = str(response.data['detail'])
            details = response.data
        elif isinstance(response.data, list):
            message = "Validation failed."
            details = {"non_field_errors": response.data}
        elif isinstance(response.data, dict):
            message = "Validation error occurred."
            details = response.data
        else:
            message = str(response.data)
            details = {}

        formatted_data = {
            "error": {
                "code": error_code,
                "message": message,
                "details": details
            }
        }
        response.data = formatted_data
        return response

    # Unhandled exceptions (500)
    logger.exception("Unhandled API exception: %s", exc)
    return Response(
        {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "details": {}
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
