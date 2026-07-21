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

- [`configs/README.md`](configs/README.md)
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

---

## Docker Deployment

SAT Builder can be run as a Docker container.

The Docker image uses `python:3.12-slim`, installs the required Python dependencies, includes the Puccini TOSCA processor, and starts the application with:

```shell
python -m src
```

Build the image from the project root:

```shell
docker build -t uowcpc/sat-builder:1.0.0 .
```

Run the container locally:

```shell
docker run --rm -p 8000:8000 uowcpc/sat-builder:1.0.0
```

Or run using Docker Compose:

```shell
docker compose up -d
```

Use a specific published version with Docker Compose:

```shell
SAT_BUILDER_VERSION=1.0.0 docker compose up -d
```

The API should then be available at:

```text
http://localhost:8000
```

The container uses `env.template` as the default runtime configuration by copying it into the image as `.env`. Local `.env` files are excluded from the Docker image.

Runtime configuration can be overridden using environment variables:

```shell
docker run --rm -p 8000:8000 \
  -e SERVER__LOG_LEVEL=debug \
  uowcpc/sat-builder:1.0.0
```

For full Docker build, run, configuration, Compose, and publishing details, see:

- [`DOCKER.md`](DOCKER.md)

---
