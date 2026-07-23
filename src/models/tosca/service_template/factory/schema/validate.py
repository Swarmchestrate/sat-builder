"""
TOSCA Template Schema Validator

Validates TOSCA templates against dynamically generated schemas with strict
enforcement of field types, constraints, and business rules.
This validator ensures templates conform to both structural requirements
and domain-specific validation rules.

Features:
- Schema validation for field types and structure
- Constraint validation for business rules
- Detailed error reporting with context
- Support for complex nested template structures
"""

import inspect
from typing import Any, Callable

from src.utils.logger import get_logger, log_validation_results, log_function_calls

logger = get_logger()

from .validate_constraints import validate_field_constraints
from .validate_schema import validate_field_schema


@log_validation_results()
def validate_tosca_schema(
        tosca_component: str,
        template_name: str,
        template_data: dict[str, Any],
        schema_data: dict[str, Any]
) -> bool:
    """
    Validate a TOSCA template against schema and constraint definitions.

    Performs comprehensive validation:
    - Required field presence (type field)
    - type recognition and support verification
    - Field-level schema validation (types, structure)
    - Business rule constraint enforcement
    - Cross-field dependency validation

    Args:
        tosca_component: Type of TOSCA template being validated (e.g., 'node')
        template_name: Identifier of the template being validated (for error context)
        template_data: Complete template configuration as key-value dictionary
        schema_data: Comprehensive schema definition including all supported types and constraints

    Returns:
        bool: True when all validations pass successfully

    Raises:
        ValueError: When any validation fails, with detailed error context:
                   - Missing required fields
                   - Unsupported types
                   - Invalid field values or types
                   - Constraint violations
                   - Schema mismatches

    Example:
        >>> sample_template_data = {
        ... "type": "swch:Application",
        ... "properties": {"image": "nginx:latest"}
        ... }
        >>> validate_tosca_schema("node", "web-server", sample_template_data, schema_data)
        True
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: validating {tosca_component} template '{template_name}'")

    # Every TOSCA template must specify its type for proper classification
    if 'type' not in template_data:
        error_msg = (
            f"{tosca_component.title()} template '{template_name}' is missing the required 'type' field. "
            f"All TOSCA templates must specify a {tosca_component} type."
        )
        logger.error(f"{function_name}: {error_msg}")
        raise ValueError(error_msg)

    # Extract clean type identifier
    # Remove namespace prefixes (e.g., 'swch:Application' → 'Application')
    if not isinstance(template_data['type'], str):
        msg = f"Invalid type '{template_data['type']}' for template '{template_name}'. Expected string type."
        logger.error(f"{function_name}: {msg}")
        raise ValueError(msg)

    type_name = template_data['type'].split(':')[-1]

    # Verify type is recognized and supported
    if type_name not in schema_data[f'{tosca_component}_types']:
        available_types = ', '.join(sorted(schema_data[f'{tosca_component}_types']))
        error_msg = (
            f"{tosca_component.title()} template '{template_name}' uses unsupported type '{type_name}'. "
            f"Supported {tosca_component} types: {available_types}"
        )
        logger.error(f"{function_name}: {error_msg}")
        raise ValueError(error_msg)

    # Retrieve validation rules for this specific type
    # Schema must exist since the type is supported above
    type_schema = schema_data['schema'][type_name]

    # Constraints are optional - some types may not have constraints defined
    type_constraints = schema_data['constraints'].get(type_name, {})

    logger.debug(
        f"{function_name}: validating {len(template_data)} field(s) for type '{type_name}'")

    # Validate each field in the template configuration
    for field_name, field_value in template_data.items():
        # Skip the type field as it's already been validated above
        if field_name == 'type':
            continue

        # Create the field path for detailed error reporting
        field_path = f"{template_name}.{field_name}"

        # Check field is allowed for this type
        if field_name not in type_schema:
            allowed_fields = sorted(type_schema.keys())
            error_msg = (
                f"Field '{field_name}' is not valid for {tosca_component} type '{type_name}' "
                f"in template '{template_name}'. "
                f"Allowed fields for {type_name}: {allowed_fields}"
            )
            logger.error(f"{function_name}: {error_msg}")
            raise ValueError(error_msg)

        # Perform structural schema validation
        # Validates data types, required structures, and format compliance
        validate_field_schema(field_path, field_value, type_schema[field_name])

        # Apply domain-specific constraint validation
        # Enforces business rules and cross-field dependencies
        validate_field_constraints(field_path, field_name, field_value, type_constraints)

    logger.debug(
        f"{function_name}: template '{template_name}' validation completed successfully")
    return True


@log_function_calls()
def manual_tosca_schema_validation(tosca_component: str, test_file: str, validate_schema: Callable) -> None:
    """
    Execute manual TOSCA template validation with comprehensive reporting.

    Loads and validates test templates from fixture files
    against current schema definitions. Provides detailed progress reporting
    and comprehensive result summaries for development and testing workflows.

    Used in Application and Capacity validation when running in manual mode.

    Args:
        tosca_component: Type of TOSCA templates to validate (e.g., 'node', 'policy')
        test_file: Name of YAML test file in tests/fixtures directory
        validate_schema: Callable function to execute schema validation

    Output:
        Prints detailed validation progress:
        - Template discovery and loading status
        - Individual template validation results
        - Error details for failed validations
        - Comprehensive validation summary with metrics
        - Success/failure indicators and recommendations
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: starting manual validation for {tosca_component} templates")

    import yaml
    from pathlib import Path

    # Construct the path to the test fixture file
    test_tosca_path = Path(__file__).parents[5] / "tests" / "fixtures" / test_file

    try:

        logger.debug(
            f"{function_name}: loading TOSCA {tosca_component} templates for validation...")



        if not test_tosca_path.exists():
            error_msg = f"Test file not found: {test_tosca_path}"
            logger.error(f"{function_name}: {error_msg}")
            return

        logger.debug(f"{function_name}: test file found at {test_tosca_path}")

        # Load and parse YAML test document
        with open(test_tosca_path, 'r', encoding='utf-8') as f:
            tosca_document = yaml.safe_load(f)

        # Extract templates from TOSCA document structure
        if tosca_component == "node":
            templates = tosca_document.get("service_template", {}).get("node_templates", {})
        elif tosca_component == "policy":
            templates = tosca_document.get("service_template", {}).get("policies", {})
        else:
            error_msg = f"{tosca_component} not found in service_template section of test file"
            logger.error(f"{function_name}: {error_msg}")
            return

        if not templates:
            error_msg = f"No {tosca_component} templates found in {test_file}"
            logger.error(f"{function_name}: {error_msg}")
            return

        # Display test suite information
        logger.debug(
            f"{function_name}: discovered {len(templates)} {tosca_component} templates")

        template_names = []
        if isinstance(templates, dict):
            template_names = list(templates.keys())
        elif isinstance(templates, list):
            for template in templates:
                template_names.extend(template.keys())
        else:
            error_msg = f"No {tosca_component} templates found in {test_file}, unexpected structure"
            logger.error(f"{function_name}: {error_msg}")
            return

        formatted_names = ', '.join(f"'{name}'" for name in sorted(template_names))
        logger.debug(f"{function_name}: templates to validate: {formatted_names}")
        logger.debug(
            f"{function_name}: starting comprehensive validation with schema and constraint checks...")
        logger.debug(f"{function_name}: {'=' * 70}")

        if isinstance(templates, dict):
            failed_validations, successful_validations = _manual_template_validation(templates, tosca_component,
                                                                                     validate_schema)
        elif isinstance(templates, list):
            successful_validations = 0
            failed_validations = 0
            for template_batch in templates:
                batch_failed, batch_successful = _manual_template_validation(template_batch, tosca_component,
                                                                             validate_schema)
                failed_validations += batch_failed
                successful_validations += batch_successful
        else:
            error_msg = f"No {tosca_component} templates found in {test_file}, unexpected structure"
            logger.error(f"{function_name}: {error_msg}")
            return

        # Generate comprehensive validation summary
        total_templates = len(templates)
        success_rate = (successful_validations / total_templates) * 100 if total_templates else 0

        logger.debug(
            f"{function_name}: validation completed - {successful_validations} passed, {failed_validations} failed")

        print(f"\n📊 VALIDATION SUMMARY REPORT")
        print("=" * 70)
        print(f"📁 Test File: {test_file}")
        print(f"📋 Total Templates Processed: {total_templates}")
        print(f"✅ Successful Validations: {successful_validations}")
        print(f"❌ Failed Validations: {failed_validations}")
        print(f"📈 Success Rate: {success_rate:.1f}%")

        # Provide actionable recommendations based on results
        if failed_validations == 0:
            logger.debug(f"{function_name}: all templates passed validation")
            print("\n🎉 EXCELLENT! All templates passed comprehensive validation! 🎉")
            print("   Your TOSCA templates are fully compliant with current schema requirements.")
            print("   Templates are ready for production deployment.")
        else:
            logger.error(
                f"{function_name}: {failed_validations}  template(s) require correction")
            print(f"\n⚠️  ATTENTION: {failed_validations} template(s) require correction")
            print("   📝 Review the validation errors above and update templates accordingly.")
            print("   🔍 Common issues include missing required fields, invalid types, or constraint violations.")
            if success_rate >= 80:
                print("   👍 Most templates are valid - you're close to full compliance!")
            elif success_rate >= 50:
                print("   🔨 Moderate validation issues detected - systematic review recommended.")
            else:
                print("   🚨 Significant validation issues - comprehensive template review required.")

    except FileNotFoundError as file_error:
        error_msg = f"Failed to locate TOSCA test configuration file: {file_error}"
        logger.error(f"{function_name}: {error_msg}")
        print(f"💥 {error_msg}")
        print(f"   📁 File Path: {test_tosca_path}")
        print(f"   💡 Ensure the test fixture directory and file exist and are accessible")

    except yaml.YAMLError as yaml_error:
        error_msg = f"Failed to parse YAML test configuration: {yaml_error}"
        logger.error(f"{function_name}: {error_msg}")
        print(f"💥 {error_msg}")
        print(f"   📄 File: {test_file}")
        print(f"   💡 Verify the test file contains valid YAML syntax")

    except Exception as system_error:
        error_msg = f"Unexpected system error during validation testing: {system_error}"
        logger.error(f"{function_name}: {error_msg}")
        print(f"💥 {error_msg}")
        print(f"   🔧 This may indicate a system configuration or dependency issue")
        import traceback
        print("\n🔍 Detailed error trace:")
        traceback.print_exc()


def _manual_template_validation(templates, tosca_component, validate_schema):
    """Validate templates and return success/failure counts."""
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: validating {len(templates)} {tosca_component} templates")

    successful_validations = 0
    failed_validations = 0

    # Execute validation for each discovered template
    for template_name, template_data in templates.items():
        try:
            logger.debug(f"{function_name}: validating template '{template_name}'")

            # Perform comprehensive validation
            validate_schema(template_name, template_data)
            logger.debug(
                f"{function_name}: template '{template_name}' passed all validation checks")
            successful_validations += 1

        except ValueError as validation_error:
            # Handle expected validation failures with detailed error context
            logger.error(
                f"{function_name}: template '{template_name}' validation failed: {validation_error}")
            failed_validations += 1

        except Exception as unexpected_error:
            # Handle unexpected system errors during validation
            logger.error(
                f"{function_name}: unexpected error validating '{template_name}': {unexpected_error}")
            failed_validations += 1

        logger.debug("-" * 50)
    return failed_validations, successful_validations
