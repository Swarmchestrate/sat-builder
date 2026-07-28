"""TOSCA validation of a generated document, via Sardou's Puccini wrapper.

The profile resolver checks what the profile declares - required properties and
their types - before a document is built. This checks the built document against
a real TOSCA processor, which covers what a resolver cannot: expression
functions, requirement and capability matching, and relationship validity.

Puccini is a binary dependency installed in the Docker image and unavailable on
some development machines, so a missing processor is reported rather than fatal.
"""
from typing import Any, Dict, List, Tuple

from src.utils.logger import get_logger, log_function_calls

logger = get_logger()


@log_function_calls()
def validate_document(document_yaml: str) -> Tuple[List[Dict[str, str]], bool]:
    """Validate a rendered TOSCA document.

    Args:
        document_yaml: The rendered document

    Returns:
        Tuple of (problems, processor_available). An empty problem list with
        processor_available False means the document was not checked at all.
    """
    try:
        from sardou import Sardou
    except ImportError as error:
        logger.warning(f"validate_document: Sardou is not installed ({error})")
        return [], False

    try:
        Sardou(content=document_yaml)
    except FileNotFoundError as error:
        # Sardou raises this both for a missing Puccini binary and a missing
        # source file; only the former can happen when passing content.
        logger.warning(f"validate_document: TOSCA processor unavailable ({error})")
        return [], False
    except Exception as error:  # noqa: BLE001 - any processor failure is a finding
        logger.warning(f"validate_document: {type(error).__name__}: {error}")
        return [{"tosca_validation": f"{type(error).__name__}: {error}"}], True

    logger.debug("validate_document: document is valid")
    return [], True
