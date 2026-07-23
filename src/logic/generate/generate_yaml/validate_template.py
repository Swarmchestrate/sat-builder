"""Template validation functionality for TOSCA YAML generation."""
import inspect
import logging
import re
from typing import List, Dict
import tempfile
import os

from sardou import Sardou

import yaml
from yaml import YAMLError

from src.utils.logger import get_logger, log_function_calls

logger = get_logger()


@log_function_calls()
def validate_template(template_yaml: str, sardou_validation=True) -> List[Dict[str, str]]:
    """Validate generated TOSCA template YAML content.

    Args:
        template_yaml: Rendered YAML template content to validate
        sardou_validation: Enable Sardou validation (optional, default: True)

    Returns:
        List of warning dictionaries from validation

    Raises:
        ValueError: When template validation encounters critical errors
        RuntimeError: When the validation process fails unexpectedly
    """
    function_name = inspect.currentframe().f_code.co_name
    validation_warnings = []

    logger.debug(f"{function_name}: Starting validation of generated template")

    # 1. Basic content validation
    content_warnings = _validate_basic_content(template_yaml)
    if content_warnings:
        validation_warnings.extend(content_warnings)

    # 2. YAML syntax validation
    try:
        parsed_yaml = yaml.safe_load(template_yaml)
        if parsed_yaml is None:
            validation_warnings.append({
                "template_rendering": "Template parsed as empty YAML - check template content"
            })
    except YAMLError as e:
        msg = f"Failed to parse YAML content: {e}"
        logger.debug(template_yaml)
        logger.error(msg, exc_info=logger.isEnabledFor(logging.DEBUG))
        raise ValueError(msg)

    # 3. TOSCA structure validation
    structure_warnings = _validate_tosca_structure(parsed_yaml)
    if structure_warnings:
        validation_warnings.extend(structure_warnings)

    # 4. Content quality validation
    quality_warnings = _validate_content_quality(template_yaml, parsed_yaml)
    if quality_warnings:
        validation_warnings.extend(quality_warnings)

    # 5. Check for rendering issues
    rendering_warnings = _check_rendering_issues(template_yaml)
    if rendering_warnings:
        validation_warnings.extend(rendering_warnings)

    # 6. Sardou validation (final check)
    if sardou_validation:
        _validate_with_sardou(template_yaml)

    logger.debug(f"{function_name}: Validation completed - Warnings: {len(validation_warnings)}")

    return validation_warnings


def _validate_basic_content(template_yaml: str) -> List[Dict[str, str]]:
    """Validate basic content requirements.

    Args:
        template_yaml: YAML content to validate

    Returns:
        List of warning dictionaries for basic content issues
    """
    warnings = []

    # Check for empty or whitespace-only content
    if not template_yaml or not template_yaml.strip():
        warnings.append({
            "template_rendering": "Generated template is empty or contains only whitespace"
        })
        return warnings

    # Check minimum length (arbitrary threshold)
    if len(template_yaml.strip()) < 20:
        warnings.append({
            "template_rendering": "Generated template content is very short - may be incomplete"
        })

    # Check for common template issues
    if template_yaml.count('\n') < 3:
        warnings.append({
            "template_rendering": "Generated template has very few lines - may be malformed"
        })

    return warnings

def _validate_tosca_structure(parsed_yaml: dict) -> List[Dict[str, str]]:
    """Validate TOSCA-specific structure requirements.

    Args:
        parsed_yaml: Parsed YAML content as dictionary

    Returns:
        List of warning dictionaries for structural issues
    """
    warnings = []

    # Required top-level fields for TOSCA templates
    required_fields = [
        "tosca_definitions_version",
        "imports",
        "metadata",
        "description",
        "service_template"
    ]

    for field in required_fields:
        if field not in parsed_yaml:
            warnings.append({
                "template_rendering": f"Missing required top-level field: '{field}'"
            })

    # Validate tosca_definitions_version format
    if "tosca_definitions_version" in parsed_yaml:
        version = parsed_yaml["tosca_definitions_version"]
        if not isinstance(version, str):
            warnings.append({
                "template_rendering": f"tosca_definitions_version must be string, got: {type(version).__name__}"
            })
        elif not re.match(r'^tosca_\d+_\d+$', version):
            warnings.append({
                "template_rendering": f"Unusual tosca_definitions_version format: '{version}'"
            })

    # Validate service_template structure
    if "service_template" in parsed_yaml:
        service_template = parsed_yaml["service_template"]
        if not isinstance(service_template, dict):
            warnings.append({
                "template_rendering": f"service_template must be dictionary, got: {type(service_template).__name__}"
            })
        else:
            # Check for expected service_template sections
            expected_sections = ["node_templates", "policies"]
            for section in expected_sections:
                if section not in service_template:
                    warnings.append({
                        "template_rendering": f"service_template missing expected section: '{section}'"
                    })

            # Validate node_templates if present
            if "node_templates" in service_template:
                node_templates = service_template["node_templates"]
                if not isinstance(node_templates, dict):
                    warnings.append({
                        "template_rendering": "node_templates must be dictionary"
                    })
                elif len(node_templates) == 0:
                    warnings.append({
                        "template_rendering": "node_templates is empty - template may be incomplete"
                    })

    # Validate imports structure if present
    if "imports" in parsed_yaml:
        imports = parsed_yaml["imports"]
        if not isinstance(imports, list):
            warnings.append({
                "template_rendering": f"imports must be list, got: {type(imports).__name__}"
            })

    # Validate metadata structure if present
    if "metadata" in parsed_yaml:
        metadata = parsed_yaml["metadata"]
        if not isinstance(metadata, dict):
            warnings.append({
                "template_rendering": f"metadata must be dictionary, got: {type(metadata).__name__}"
            })

    return warnings

def _validate_content_quality(template_yaml: str, parsed_yaml: dict) -> List[Dict[str, str]]:
    """Validate content quality and completeness.

    Args:
        template_yaml: Raw YAML content
        parsed_yaml: Parsed YAML content as dictionary

    Returns:
        List of warning dictionaries for quality issues
    """
    warnings = []

    # Check for placeholder values that might indicate incomplete rendering
    placeholder_patterns = [
        r'TODO',               # TO DO comments
        r'FIXME',              # FIX ME comments
        r'<PLACEHOLDER>',      # Explicit placeholders
        r'null',               # Null values that might be unintended
        r'\[\]',               # Empty lists (escaped brackets)
        r'\{\}'                # Empty dictionaries (escaped braces)
    ]

    for pattern in placeholder_patterns:
        matches = re.findall(pattern, template_yaml, re.IGNORECASE)
        if matches:
            warnings.append({
                "template_rendering": f"Found potential placeholder content: {matches[:3]}..."  # Show the first 3 matches
            })

    # Check for very generic or default values
    if parsed_yaml:
        description = parsed_yaml.get("description", "")
        if isinstance(description, str):
            generic_descriptions = [
                "template description",
                "tosca template",
                "default description",
                "generated template"
            ]
            if any(generic.lower() in description.lower() for generic in generic_descriptions):
                warnings.append({
                    "template_rendering": f"Description appears to be generic: '{description}'"
                })
            if len(description) < 10:
                warnings.append({
                    "template_rendering": f"Description is very short: '{description}'"
                })

    # Check indentation consistency
    lines = template_yaml.split('\n')
    indent_sizes = set()
    for line in lines:
        if line.strip() and line.startswith(' '):
            leading_spaces = len(line) - len(line.lstrip(' '))
            if leading_spaces > 0:
                indent_sizes.add(leading_spaces)

    if len(indent_sizes) > 3:  # More than 3 different indentation levels might indicate issues
        warnings.append({
            "template_rendering": f"Inconsistent indentation detected - found {len(indent_sizes)} different indent sizes"
        })

    # Check for excessively long lines
    max_line_length = 120  # Reasonable limit for YAML
    long_lines = [i+1 for i, line in enumerate(lines) if len(line) > max_line_length]
    if long_lines:
        warnings.append({
            "template_rendering": f"Found {len(long_lines)} lines exceeding {max_line_length} characters (lines: {long_lines[:5]})"
        })

    return warnings

def _check_rendering_issues(rendered_yaml: str) -> List[Dict[str, str]]:
    """Check for common rendering issues in the output.

    Args:
        rendered_yaml: Rendered YAML content

    Returns:
        List of warning dictionaries for any issues found
    """
    warnings = []

    # Check for unrendered Jinja variables
    if "{{" in rendered_yaml or "}}" in rendered_yaml:
        warnings.append({
            "template_rendering": "Found unrendered Jinja variables in output - check template syntax"
        })

    # Check for unrendered Jinja blocks
    if "{%" in rendered_yaml or "%}" in rendered_yaml:
        warnings.append({
            "template_rendering": "Found unrendered Jinja blocks in output - check template logic"
        })

    # Check for empty sections that might indicate missing data
    lines = rendered_yaml.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.endswith(':') and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            # Check if the next line is empty or starts a new section at the same level
            if not next_line or (not next_line.startswith(' ') and ':' in next_line):
                section_name = stripped.rstrip(':')
                if section_name in ['service_template', 'node_templates', 'policies', 'imports', 'metadata']:
                    warnings.append({
                        "template_rendering": f"Section '{section_name}' appears to be empty - verify template data"
                    })

    # Check for very short output that might indicate rendering failure
    if len(rendered_yaml.strip()) < 50:  # Arbitrary threshold
        warnings.append({
            "template_rendering": "Rendered template is very short - verify template completeness"
        })

    return warnings


def _validate_with_sardou(template_yaml: str) -> None:
    """Validate TOSCA template using the Sardou library.

   Args:
       template_yaml: YAML template content to validate

   Returns:
       List of warnings from Sardou validation
   """
    function_name = inspect.currentframe().f_code.co_name

    # Create temporary file with YAML content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
        temp_file.write(template_yaml)
        temp_file_path = temp_file.name


    logger.debug(f"{function_name}: Running Sardou validation on temporary file")
    _ = Sardou(temp_file_path)
    logger.debug(f"{function_name}: Sardou validation completed successfully")

    # Clean up temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)