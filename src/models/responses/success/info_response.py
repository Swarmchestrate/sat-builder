from pydantic import BaseModel, Field

from src.models.app import get_info_config

info_cfg = get_info_config()


class InfoResponse(BaseModel):
    """Info endpoint API information response."""

    title: str = Field(default_factory=lambda: info_cfg["title"], description="API title")
    version: str = Field(default_factory=lambda: info_cfg["version"], description="API version")
    description: str = Field(default_factory=lambda: info_cfg["description"], description="API description")
    license: dict = Field(default_factory=lambda: info_cfg["license"], description="License information")
    contact: dict = Field(default_factory=lambda: info_cfg["contact"], description="Contact information")
    docs: str = Field(default_factory=lambda: info_cfg["docs"], description="Swagger documentation URL")
    redoc: str = Field(default_factory=lambda: info_cfg["redoc"], description="ReDoc documentation URL")
    openapi: str = Field(default_factory=lambda: info_cfg["openapi"], description="OpenAPI schema URL")

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Swarmchestrate Application Template Builder API",
                "version": "1.0.0",
                "description": "OpenAPI-compatible RESTful API for generating Swarmchestrate Application Templates (SAT). This API validates and generates TOSCA-based templates in YAML or JSON format.",
                "license": {"name": "Apache 2.0", "url": "https://apache.org/licenses/LICENSE-2.0"},
                "contact": {"name": "GitHub Issues", "url": "https://github.com/Swarmchestrate/sat-builder/issues"},
                "docs": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json"
            }
        }
    }
