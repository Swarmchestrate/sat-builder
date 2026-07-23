class ErrorMessage:
    """Centralized validation error messages."""
    EMPTY_TYPE = '{field_name} cannot be an empty {expected_type}'
    INVALID_TYPE = '{field_name} must be a {expected_type}, got {actual_type}'
    WHITESPACE_ONLY = '{field_name} cannot be whitespace-only'
    WHITESPACE_PADDING = '{field_name} cannot have leading or trailing whitespace'
    INVALID_CHARACTERS = '{field_name} must contain only {allowed_chars}'
    INVALID_ASCII = '{field_name} must contain only ASCII characters'
    MIN_LENGTH = '{field_name} must be at least {min_length} characters long'
    MAX_LENGTH = '{field_name} must not exceed {max_length} characters'
    LIST_DUPLICATES = '{field_name} cannot contain duplicates: {duplicates}'
    INVALID_URL_SCHEME = '{field_name} must be a valid URL starting with {schemes}'
    INVALID_URL_DOMAIN = '{field_name} must contain a valid domain name'
    INVALID_DATES = '{second_date_name} date cannot be before {first_date_name}'
