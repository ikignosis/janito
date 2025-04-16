# Release Notes – Version 1.3

## Changed

- Removed support for the `USE_AZURE_OPENAI` environment variable. The Azure OpenAI client is now enabled by setting the `use_azure_openai` value in the configuration (default: `false`).
  - If you previously relied on `USE_AZURE_OPENAI`, please update your configuration to set `use_azure_openai` accordingly.

- Removed support for the `AZURE_OPENAI_ENDPOINT` environment variable. The Azure OpenAI client now uses the `base_url` value from the configuration instead. This simplifies configuration management and ensures all endpoints are set via config files or CLI options.
  - If you previously relied on `AZURE_OPENAI_ENDPOINT`, please update your configuration to set the correct `base_url`.

- Removed support for the `AZURE_OPENAI_API_VERSION` environment variable. The Azure OpenAI client now uses the `azure_openai_api_version` value from the configuration instead (default: `2023-05-15`).
  - If you previously relied on `AZURE_OPENAI_API_VERSION`, please update your configuration to set the correct `azure_openai_api_version`.

## Other

- No other user-facing changes in this release.
