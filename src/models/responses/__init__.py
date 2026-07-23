"""
Response Models Package

This package contains all response model definitions for the SAT Builder API.
Response models are organized into successful responses and error responses.

API Responses:
- InfoResponse: API information and documentation links
- HealthResponse: Service health status and metadata  
- BuildResponse: Generated TOSCA templates in requested formats

Error Responses:
- InvalidInputResponse: 400 Bad Request errors
- ValidationErrorResponse: 422 Validation errors  
- InternalServerErrorResponse: 500 Internal Server errors

Usage:

"""

from src.models.responses.error.error_responses import (
    BaseErrorResponse
)
from .error.internal_server_error_response import InternalServerErrorResponse
from .error.validation_error_response import ValidationErrorResponse
from .error.invalid_input_response import InvalidInputResponse
from .success.health_response import HealthResponse
from .success.info_response import InfoResponse
from .success.build_response import get_build_response_class

__all__ = [
    # API Success Responses
    "InfoResponse",
    "HealthResponse",
    "get_build_response_class",

    # Error Responses
    "BaseErrorResponse",
    "InvalidInputResponse",
    "ValidationErrorResponse",
    "InternalServerErrorResponse"
]
