"""TOSCA model factory utilities for creating reusable Pydantic model classes.

Provides factory functions for generating TOSCA data models that can be
customized for different contexts (application vs capacity) while sharing
common validation logic and structure.

Key components:
- Factory functions for imports, metadata, templates, and versioning
- Shared base tosca_types like DefinitionsVersion and Description
- Dynamic model generation based on TOSCA file configurations
"""

from .service_template_node_templates import get_node_templates_class
from .service_template_policies import get_policies_class

__all__ = [
    "get_node_templates_class",
    "get_policies_class",
]
