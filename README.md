# SAT Builder

Swarmchestrate Application Template Builder - A RESTful API for generating TOSCA-based Application and Capacity templates.

---

## Features

- Generate Swarmchestrate Application Templates (SAT) in YAML and/or JSON format.
- Support Application and Capacity templates.
- Support additional template types through configuration.
- Render templates using Jinja-based YAML templates.
- Support template versioning for backward compatibility and incremental updates.
- Support TOSCA validation and processing with tools such as the [Sardou TOSCA Toolkit](https://pypi.org/project/Sardou/).
- Provide a FastAPI-based RESTful API with OpenAPI compatibility.
- Generate dynamic OpenAPI schemas and constraints based on configurable TOSCA definition files.
- Use TOSCA definitions in the request body.
- Provide default TOSCA definitions based on configurable TOSCA definition files.
- Provide interactive API documentation with Swagger UI.
- Include comprehensive logging.
- Support Docker-based deployment.

---

## Before Starting

### Configuration and Template Rendering

The Template Builder is driven by two main areas:

- **Configuration files** — define API behavior, supported template types, validation rules, default request structures, schema constraints, and response settings.
- **Rendering templates** — Jinja-based YAML templates used to generate the final TOSCA Application and Capacity templates.

For more details, see:

- [`config/README.md`](config/README.md)
- [`templates/README.md`](templates/README.md)

### Configuration

The main configuration files are:

- `app.yaml`
- `tosca_application_template.yaml`
- `tosca_capacity_template.yaml`

These files define API metadata, routers, supported template types, TOSCA defaults, schema constraints, and validation settings.

During startup, the service uses the TOSCA configuration files to generate OpenAPI and JSON schema files for Application and Capacity node templates and policies.

> [!WARNING]
> Configuration changes can affect API behavior, generated schemas, validation, and client integrations.

### Template Rendering

Rendering templates are split by template type, such as Application and Capacity.

Template versions are determined from numeric YAML filenames, for example:

- `001.yaml`
- `002.yaml`
- `003.yaml`

The highest available numeric version is treated as `latest`.

Templates can be deprecated by adding `_depr` to the filename, for example:

- `001_depr.yaml`

> [!NOTE]
> Rendering files use Jinja syntax and must produce valid YAML after rendering. Indentation is critical.

### Generation Flow

At a high level:

1. `app.yaml` defines the available template types, routes, validation settings, and template directories.
2. The TOSCA configuration files define default structures and schema constraints.
3. The service generates OpenAPI and JSON schemas during startup.
4. The API validates incoming requests.
5. The selected Jinja template renders the final TOSCA output.
6. The API returns the result as YAML, JSON, or both, depending on the configured response type.