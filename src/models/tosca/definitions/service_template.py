"""
TOSCA Service Template Factory

Creates dynamic Pydantic model classes for TOSCA service templates with integrated
validation, schema generation, and template processing capabilities. Provides
comprehensive service template modeling with node templates and policies support,
including namespace management and resource extraction functionality.
"""

import inspect
from typing import Optional, Tuple, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, ValidationError
from ruamel.yaml import YAML

from src.models.tosca.service_template import get_node_templates_class, get_policies_class
from src.utils.config import get_config_file_path
from src.utils.logger import get_logger

logger = get_logger()

# Module-level cache for performance
_SERVICE_TEMPLATE_CACHE = {}


def get_service_template_class(tosca_type: str, tosca_file_name: str) -> type[BaseModel]:
    """Create a dynamic Pydantic model for TOSCA service templates with advanced processing capabilities.

    Generates a ServiceTemplate class that combines node templates and policies with comprehensive
    validation, caching, and template transformation features including namespace management
    and automatic resource extraction from node filters.

    Args:
        tosca_type: TOSCA type identifier for template categorization
        tosca_file_name: Configuration file name (without .yaml extension) containing
                        service_template with node_templates and policies sections

    Returns:
        ServiceTemplate class with:
        - node_templates: Collection of TOSCA node templates with validation
        - policies: Optional collection of TOSCA policies
        - update_service_template(): Method for namespace and resource processing
        - Comprehensive validation and schema generation capabilities

    Raises:
        ValueError: When required sections (service_template, node_templates, policies)
                   are missing from the config file or template processing fails

    Note:
        Uses module-level caching for performance optimization. The returned ServiceTemplate
        class includes methods for namespace removal/addition and automatic resource extraction
        from application node filters.
    """

    # noinspection DuplicatedCode
    def _load_service_template_data() -> tuple[dict, dict]:
        """Load TOSCA service template data with caching.

        Returns:
            Tuple of (node_templates_data, policies_data) from config file

        Raises:
            ValueError: When required sections are missing
        """
        function_name = inspect.currentframe().f_code.co_name

        # Performance optimization: check cache before expensive file operations
        cache_key = (tosca_type, tosca_file_name)
        if cache_key in _SERVICE_TEMPLATE_CACHE:
            logger.debug(f"{function_name}: '{tosca_file_name}' cache hit")
            return _SERVICE_TEMPLATE_CACHE[cache_key]

        logger.debug(f"{function_name}: '{tosca_file_name}' cache miss, building...")

        # Load and parse YAML configuration file
        tosca_file = get_config_file_path(tosca_file_name)
        yaml = YAML(typ='safe', pure=True)

        with open(tosca_file, 'r', encoding='utf-8') as f:
            tosca_data = yaml.load(f)

        if "service_template" not in tosca_data:
            msg = f"Missing 'service_template' section in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)

        service_template_data = tosca_data['service_template']

        if "node_templates" not in service_template_data:
            msg = f"Missing 'node_templates' section in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)

        if "policies" not in service_template_data:
            msg = f"Missing 'policies' section in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)

        node_templates = service_template_data['node_templates']
        policies = service_template_data['policies']
        # Cache for future requests - thread-safe dictionary operation
        _SERVICE_TEMPLATE_CACHE[cache_key] = (node_templates, policies)
        logger.debug(f"{function_name}: '{tosca_file_name}' cached for future use")
        return node_templates, policies

    # Load examples with caching
    node_templates_example, policies_example = _load_service_template_data()

    # Create collection classes
    # noinspection PyPep8Naming
    NodeTemplates = get_node_templates_class(tosca_type, tosca_file_name)
    # noinspection PyPep8Naming
    Policies = get_policies_class(tosca_type, tosca_file_name)

    class ServiceTemplate(BaseModel):
        """TOSCA service template with comprehensive validation and schema generation."""

        node_templates: NodeTemplates = Field(
            ...,
            description="Collection of TOSCA node templates",
            examples=[node_templates_example]
        )
        policies: Optional[Policies] = Field(
            default=None,
            description="Collection of TOSCA policies",
            examples=[policies_example]
        )

        model_config = ConfigDict(
            extra="forbid"
        )

        def update_service_template(self, namespace: str, extract_resources: bool = False) -> Tuple[
            'ServiceTemplate', List[Dict[str, str]]]:
            """Update the service template with optional resource extraction.

            Args:
                namespace: Expected namespace for validation
                extract_resources: Whether to extract node_filters and create resources

            Returns:
                Tuple of (updated_service_template, warnings_list)
            """
            warnings = []

            # Start with the current instance
            updated_template = self

            # Remove namespace
            # noinspection PyProtectedMember
            updated_template, remove_namespace_warnings = updated_template._remove_namespace(namespace)
            warnings.extend(remove_namespace_warnings)

            # Conditionally extract resources if requested
            if extract_resources:
                # noinspection PyProtectedMember
                updated_template, resource_warnings = updated_template._extract_and_create_resources()
                warnings.extend(resource_warnings)

            # Add namespace back
            # noinspection PyProtectedMember
            updated_template, add_namespace_warnings = updated_template._add_namespace(namespace)
            warnings.extend(add_namespace_warnings)

            return updated_template, warnings

        def _remove_namespace(self, namespace: str) -> Tuple['ServiceTemplate', List[Dict[str, str]]]:
            """Remove namespace prefixes from all node types and policy types."""
            warnings = []

            def _process_namespace_removal(data: Dict[str, Any], item_name: str, item_type: str) -> Dict[str, Any]:
                """A helper function to process namespace removal for both nodes and policies."""
                modified_item = data.copy()

                if "type" in modified_item:
                    type_value = modified_item["type"]
                    if ":" in type_value:
                        found_namespace = type_value.split(":", 1)[0]
                        warnings.append({
                            "service_template": f"Namespace removed - namespace '{found_namespace}' for {item_type} '{item_name}' type '{type_value}'"
                        })
                        modified_item["type"] = type_value.split(":", 1)[1]
                        if found_namespace != namespace:
                            warnings.append({
                                "service_template": f"Namespace mismatch - {item_type.title()} '{item_name}' type '{type_value}' does not match namespace '{namespace}'"
                            })

                return modified_item

            # Process node templates
            current_node_templates = self.node_templates.model_dump()
            modified_node_templates = {}

            for node_name, node_config in current_node_templates.items():
                modified_node_templates[node_name] = _process_namespace_removal(node_config, node_name, "node")

            # Process policies
            modified_policies = None
            if self.policies:
                current_policies = self.policies.model_dump()
                modified_policies = []

                for policy_dict in current_policies:
                    modified_policy_dict = {}

                    for policy_name, policy_data in policy_dict.items():
                        modified_policy_dict[policy_name] = _process_namespace_removal(policy_data, policy_name, "policy")

                    modified_policies.append(modified_policy_dict)

            modified_data = {
                "node_templates": modified_node_templates,
                "policies": modified_policies
            }

            validated_template = ServiceTemplate(**modified_data)
            return validated_template, warnings

        def _extract_and_create_resources(self) -> Tuple['ServiceTemplate', List[Dict[str, str]]]:
            """Extract node_filters from applications and create corresponding resources."""

            warnings = []
            current_node_templates = self.node_templates.model_dump()
            modified_node_templates = current_node_templates.copy()

            generated_resources = {}
            resource_counter = 1

            # Get all existing node names to avoid conflicts
            all_existing_names = set(current_node_templates.keys())

            # 1. Scan for applications with node_filter requirements
            for app_name, app_config in current_node_templates.items():
                if app_config.get("type") == "Application":  # No namespace prefix after removal
                    requirements = app_config.get("requirements", [])

                    for i, req in enumerate(requirements):
                        if "host" in req and isinstance(req["host"], dict) and "node_filter" in req["host"]:
                            # 2. Extract node_filter constraints
                            node_filter = req["host"]["node_filter"]

                            # 3. Generate unique resource name
                            resource_name = f"generated-resource-{resource_counter}"

                            # Find next available name if conflict exists
                            if resource_name in all_existing_names:
                                temp_counter = resource_counter
                                while f"generated-resource-{temp_counter}" in all_existing_names:
                                    temp_counter += 1

                                warnings.append({
                                    "service_template": f"Resource Extraction - Resource name '{resource_name}' for Application: {app_name} already exists, using 'generated-resource-{temp_counter}' instead"
                                })

                                resource_name = f"generated-resource-{temp_counter}"

                            # Create the resource (no duplication)
                            generated_resources[resource_name] = {
                                "type": "Resource",  # No namespace prefix after removal
                                "directives": ["select"],
                                "node_filter": node_filter
                            }
                            all_existing_names.add(resource_name)

                            # 4. Replace application requirement with direct reference
                            modified_node_templates[app_name]["requirements"][i] = {
                                "host": resource_name
                            }

                            warnings.append({
                                "service_template": f"Resource Extraction - Extracted node_filter from Application: '{app_name}' and created Resource: '{resource_name}'"
                            })

                            resource_counter += 1

            # 5. Merge new resources into node_templates
            modified_node_templates.update(generated_resources)

            # Create the new ServiceTemplate
            modified_data = {
                "node_templates": modified_node_templates,
                "policies": self.policies.model_dump() if self.policies else None
            }

            try:
                validated_template = ServiceTemplate(**modified_data)
                if generated_resources:
                    logger.info(f"Resource extraction completed - created {len(generated_resources)} resources")
                else:
                    logger.info("Resource extraction completed - no node_filters found")
                return validated_template, warnings
            except ValidationError as e:
                msg = f"Resource extraction created invalid service template: {e}"
                logger.error(msg)
                raise ValueError(msg)

        def _add_namespace(self, namespace: str) -> Tuple['ServiceTemplate', List[Dict[str, str]]]:
            """Add namespace prefixes to all node types and policy types.

            This function expects types to NOT have namespace prefixes already.
            If a colon is found in any type, it indicates a bug in the processing flow.
            """
            warnings = []

            def _process_namespace_addition(data: Dict[str, Any], item_name: str, item_type: str) -> Dict[str, Any]:
                """A helper function to process namespace addition for both nodes and policies."""
                modified_item = data.copy()

                if "type" in modified_item:
                    type_value = modified_item["type"]
                    if ":" in type_value:
                        msg = f"service_template: {item_type.title()} '{item_name}' type '{type_value}' already contains namespace - this should not happen after namespace removal"
                        logger.error(msg)
                        raise ValueError(msg)

                    modified_item["type"] = f"{namespace}:{type_value}"
                    warnings.append({
                        "service_template": f"Namespace Addition Added namespace '{namespace}' to {item_type} '{item_name}' type '{type_value}'"
                    })

                return modified_item

            # Process node templates
            current_node_templates = self.node_templates.model_dump()
            modified_node_templates = {}

            for node_name, node_config in current_node_templates.items():
                modified_node_templates[node_name] = _process_namespace_addition(node_config, node_name, "node")

            # Process policies
            modified_policies = None
            if self.policies:
                current_policies = self.policies.model_dump()
                modified_policies = []

                for policy_dict in current_policies:
                    modified_policy_dict = {}

                    for policy_name, policy_data in policy_dict.items():
                        modified_policy_dict[policy_name] = _process_namespace_addition(policy_data, policy_name, "policy")

                    modified_policies.append(modified_policy_dict)

            modified_data = {
                "node_templates": modified_node_templates,
                "policies": modified_policies
            }

            validated_template = ServiceTemplate(**modified_data)
            return validated_template, warnings

    return ServiceTemplate