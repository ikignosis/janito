# Changelog

All notable changes to this project will be documented in this file.

## [2.3.0] - 2025-06-25
### Added
- requirements-dev.txt with development dependencies (pytest, pre-commit, ruff, detect-secrets, codespell, black) for code quality and testing
- Java outline support to get_file_outline tool, including package-private methods
- create_driver method to AzureOpenAIProvider for driver instantiation
- CLI --version test and suppress pytest-asyncio deprecation warning
- New dependencies: prompt_toolkit, lxml, requests, bs4 to requirements.txt

### Changed
- Improved error messages and documentation
- Refined error handling in open_html_in_browser.py and open_url.py
- Refactor remove_file tool: use ReportAction.DELETE for all file removal actions
- Remove redundant _prepare_api_kwargs override in AzureOpenAIModelDriver
- Refactor(azure_openai): use 'model' directly in API kwargs, remove deployment_name remapping
- Add public read-only driver_config property to AzureOpenAIProvider
- Add _prepare_api_kwargs to support deployment_name for Azure OpenAI API compatibility
- Update toolbar bindings: add CTRL-C for interrupt/exit, clarify F1 usage
- Update pyproject.toml optional-dependencies section for setuptools compatibility
- Remove references to max_results in FindFilesTool docstring
- Refactor: use .jsonl extension for input history files instead of .log
- Refactor get_file_outline core logic to remove duplication and add tests
- Test CLI: Ensure error on missing provider and validate supported models output for each provider
- Configure dynamic dependencies in pyproject.toml
- Define dependencies in requirements.txt: attrs, rich, pathspec, setuptools, pyyaml, jinja2
- Add workdir support to LocalToolsAdapter and CLI; improve Python tool adapters
- Friendly error message when the provider is not present from the available ones

### Fixed
- Ensure error on missing provider and validate supported models output for each provider
- Update supported models table; remove o4-mini-high model from code and docs

## [2.1.1] - 2024-06-23
### Changed
- Bumped version to 2.1.1 in `version.py`, `pyproject.toml`, and `__init__.py`.
- docs: add DeepSeek setup guide, update navigation and references
    - Add docs/deepseek-setup.md with setup instructions for DeepSeek provider
    - Link DeepSeek setup in docs/index.md and mkdocs.yml navigation
    - Fix model name: change 'deepseek-coder' to 'deepseek-reasoner' in DeepSeek provider and model_info
    - Update DeepSeek provider docstrings and options to match supported models

## [2.1.0] - 2024-06-09
### Added

### Changed
- Bumped version to 2.1.0 in `version.py`, `pyproject.toml`, and `__init__.py`.

---

*Older changes may not be listed.*
