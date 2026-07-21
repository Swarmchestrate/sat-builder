# Swarmchestrate Template Rendering Files

This directory contains Jinja-based YAML templates used by the Swarmchestrate Template Builder to render TOSCA service templates.

The templates generate YAML output from API-provided template data, including TOSCA definitions, imports, metadata, node templates, requirements, node filters, properties, and policies.

## Files Overview

Templates are split into separate folders for Application and Capacity templates.

Template versions are determined from the numeric YAML filenames, for example:

- `001.yaml`
- `002.yaml`
- `003.yaml`

When the service initializes, it identifies the available template versions and makes them available through the API. The highest available numeric version is treated as `latest`.

A template can be deprecated by adding `_depr` to the filename, for example:

- `001_depr.yaml`

Deprecated templates are kept for reference or backward compatibility, but they should not be used for new template generation unless explicitly required.

## Versioning

Template versioning serves multiple purposes:

- Backward compatibility.
- Incremental updates.
- Testing new template structures.
- Supporting different request body formats over time.

If a requested template version is incompatible with the request body, the API returns an error.

## Notes

- These files are templates, not plain YAML files.
- They use Jinja syntax to dynamically generate YAML output.
- Indentation is critical because the rendered output must remain valid YAML.
- Changes should be tested by rendering example Application and Capacity templates.
- If Sardou TOSCA validation is enabled in `app.yaml`, generated templates should also pass TOSCA validation after rendering.
- The default response type is configured in the relevant TOSCA configuration file. If the response type is set to JSON only, the API returns the generated template as JSON instead of YAML.