import os

from src.utils.logger import get_logger

logger = get_logger()


def _get_available_templates():
    """Get list of template YAML files that are numeric identifiers."""
    yaml_files = [f for f in os.listdir("templates")
                  if f.endswith('.yaml') and f[:-5].isdigit()]
    return [f[:-5] for f in yaml_files]  # Remove .yaml extension


def _get_latest_template(available_templates):
    """Find the latest template version by numeric comparison."""
    return max(available_templates, key=int)


def process_metadata(metadata):
    """Process metadata and resolve template version."""
    available_templates = _get_available_templates()
    template_version = metadata["version"]
    if template_version == "latest":
        latest_template = _get_latest_template(available_templates)
        return latest_template, None
    elif template_version in available_templates:
        return template_version, None
    else:
        return None, f"Invalid template version: {template_version}"
