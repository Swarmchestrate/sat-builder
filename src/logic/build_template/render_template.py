from pathlib import Path

from jinja2 import Template

from src.utils.logger import get_logger

logger = get_logger()


def render_template(template_version: str, tosca: dict):
    """Load and render a Jinja2 template with TOSCA data."""

    project_root = Path(__file__).parent.parent
    templates_dir = project_root / "templates"
    template_path = templates_dir / f"{template_version}.yaml"
    if not template_path.exists():
        return None, f"No template file found for version '{template_version}'"

    # Load template content
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    template = Template(template_content)
    rendered_output = template.render(tosca=tosca)

    return {"tosca_output": rendered_output}, None
