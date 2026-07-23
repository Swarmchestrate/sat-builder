from typing import Optional, Any
from urllib.parse import urlparse

from src.utils.logger import get_logger
from .helpers.error_messages import ErrorMessage
from .string_validator import StringValidator

logger = get_logger()


class UrlValidator:
    """Handles URL validation operations."""

    @staticmethod
    def validate_url(
            url_str: str,
            url_field: str,
            allowed_schemes: tuple[str, ...] = ('http', 'https'),
            pattern: Optional[str] = None,
            pattern_description: Optional[str] = None
    ) -> str:
        """Validate URL format and scheme."""
        url_checked = StringValidator.validate_string(
            url_str,
            url_field,
            ascii_only=True,
            pattern=pattern,
            pattern_description=pattern_description
        )
        url_parsed = urlparse(url_checked)
        UrlValidator._check_url_scheme(url_parsed, url_field, allowed_schemes)
        UrlValidator._check_url_domain(url_parsed, url_field)
        return url_checked

    @staticmethod
    def _check_url_scheme(
            url_parsed: Any,
            url_field: str,
            allowed_schemes: tuple[str, ...]) -> None:
        """Validate that URL scheme is present and allowed."""
        if not url_parsed.scheme or url_parsed.scheme not in allowed_schemes:
            schemes_str = '://, '.join(allowed_schemes) + '://'
            msg = ErrorMessage.INVALID_URL_SCHEME.format(
                field_name=url_field,
                schemes=schemes_str
            )
            logger.error(msg)
            raise ValueError(msg)

    @staticmethod
    def _check_url_domain(
            url_parsed: Any,
            url_field: str
    ) -> None:
        """Validate that URL domain is present."""
        if not url_parsed.netloc:
            msg = ErrorMessage.INVALID_URL_DOMAIN.format(
                field_name=url_field
            )
            logger.error(msg)
            raise ValueError(msg)
