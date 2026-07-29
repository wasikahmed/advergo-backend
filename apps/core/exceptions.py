import logging

from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Wraps DRF's default handler to produce a consistent error envelope
    and log unhandled exceptions with request context."""
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception in %s", context.get("view"))
        return response

    response.data = {
        "detail": response.data.get("detail", response.data)
        if isinstance(response.data, dict)
        else response.data,
        "errors": response.data if isinstance(response.data, (dict, list)) else None,
    }
    return response
