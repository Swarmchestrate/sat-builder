"""
Project Root Utilities

This module provides functionality for detecting and resolving the project root directory.
Essential for ensuring consistent file path resolution across different execution contexts.
"""

# Import project root detection utility
from .project_root import get_project_root  # Function to locate the project's root directory

# Public API - expose project root functionality
__all__ = ['get_project_root']
