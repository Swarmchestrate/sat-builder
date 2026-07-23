"""Project root utilities."""
from functools import lru_cache
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger()


@lru_cache(maxsize=1)  # Fix #20: Cache project root lookup
def get_project_root() -> Path:
    """
    Find project root by looking for common project indicators.

    Searches upward from current file location for:
    - src/ directory
    - pyproject.toml, setup.py, or requirements.txt
    """
    current = Path(__file__).resolve()

    # Try walking up to find project root indicators
    for parent in [current.parent] + list(current.parents):
        # Look for src directory (most reliable indicator)
        if (parent / "src").is_dir():
            return parent

        # Look for common project files, then verify src exists
        project_files = ["pyproject.toml", "setup.py", "requirements.txt", ".git"]
        if any((parent / file).exists() for file in project_files):
            # Check src exists only once here
            src_dir = parent / "src"
            if src_dir.is_dir():
                return parent

    # Remove unreliable fallback, raise clear error instead
    raise RuntimeError(
        "Could not find project root directory with src/ folder. "
        "Make sure you're running this from within a project that has a src/ directory "
        "and contains pyproject.toml, setup.py, requirements.txt, or .git"
    )
