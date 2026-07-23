"""Configuration Loader"""

from pathlib import Path
from typing import Any, Dict

from ruamel.yaml import YAML

from src.utils.logger import get_logger
from src.utils.project import get_project_root

logger = get_logger()


def get_config_file_path(config_file_name: str, config_dir: str = "configs") -> Path:
    """Get path to config file."""
    return get_project_root() / config_dir / f"{config_file_name}.yaml"


def get_config(key_path: list, config_file_name: str, config_dir: str = "configs") -> tuple[
    Dict[str, Any], Dict[str, Any]]:
    """Get config section by key path."""
    document = _load_document(config_file_name, config_dir)
    current_section = _get_config_section(document, key_path, config_file_name)
    return current_section, document


def _load_document(config_file_name: str, config_dir: str = "configs") -> Dict[str, Any]:
    """Load YAML document."""
    config_file_path = get_config_file_path(config_file_name, config_dir)
    yaml_parser = YAML(typ='safe', pure=True)

    with open(config_file_path, 'r', encoding='utf-8') as file:
        return yaml_parser.load(file)


def _get_config_section(document: dict[str, Any], key_path: list, config_file_name: str) -> Any:
    """Navigate nested config document using key path."""
    current_section = document
    navigation_path = []

    for key in key_path:
        navigation_path.append(key)

        if key not in current_section:
            path_format = ']['.join(navigation_path)
            raise ValueError(f"Missing '{key}' key in {config_file_name} at path: [{path_format}]")

        current_section = current_section[key]

    return current_section
