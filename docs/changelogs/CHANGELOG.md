# Changelog

All notable changes to this project will be documented in this file.

## [2.27.0] - 2025-08-16

### Added

- **Enhanced CLI Experience**:
  - **One-Shot Mode Prefix Support**: Added `/rwx` prefix support to enable all tool permissions in a single command
    - Use `/rwx "your prompt here"` to enable read, write, and execute permissions in one-shot mode
    - Equivalent to using `-r -w -x` flags but more convenient for quick tasks
    - Maintains security by requiring explicit user action for each command

- **Enhanced Web Fetching**:
  - **Browser-like Session Support**: Enhanced `fetch_url` tool with browser-like session capabilities
    - Persistent session management for improved reliability
    - Better handling of cookies and session state
    - Enhanced user-agent and header management
    - Improved error handling for network requests

### Changed

- **Improved Documentation**:
  - Updated CLI documentation to reflect new `/rwx` prefix and one-shot mode features
  - Enhanced fetch_url tool documentation with new session parameters
  - Improved parameter descriptions and usage examples

### Fixed

- **Documentation Fixes**:
  - Added missing docstring parameters for fetch_url tool
  - Fixed parameter documentation inconsistencies

## [2.26.0] - 2025-08-16

### Added

- **Chat Mode Shell Enhancements**:
  - **Unrestricted Mode Command**: Added new `/unrestricted` command to chat mode shell
    - Toggle unrestricted mode equivalent to the `-u` CLI flag
    - Real-time switching between restricted and unrestricted modes
    - Visual feedback with color-coded status messages
    - Integration with URL whitelist manager for comprehensive security control
    - **Security Warning**: Clear indication when unrestricted mode is enabled (DANGEROUS - no path or URL restrictions)

### Security

- **Enhanced Security Controls**: 
  - URL whitelist manager integration with unrestricted mode toggle
  - Path security controls synchronized with shell state
  - Real-time security status updates in chat mode

## [2.25.0] - 2025-08-15

### Added

- **Loop Protection System**: Comprehensive protection against excessive file operations
  - **File Creation Protection**: Prevents creation of more than 5 files within 10 seconds to the same path
  - **File Reading Protection**: Prevents reading the same file more than 10 times within 10 seconds
  - **Directory Traversal Protection**: Prevents excessive directory operations
  - **Cross-Tool Protection**: Loop protection is shared across all local tools to prevent abuse

- **Enhanced Path Handling**: 
  - **Tilde Expansion**: Support for `~` (user home directory) and `~username` expansion in file paths
  - **Path Validation**: Enhanced validation for file paths with better error messages
  - **Cross-Platform Support**: Improved Windows/Unix path handling

- **Security Improvements**:
  - **Path Security**: Enhanced path validation and sanitization
  - **Access Control**: Better handling of restricted directories and files
  - **Input Validation**: Improved validation for all user-provided paths

- **Plugin System Enhancements**:
  - **Remote Plugin Support**: Full support for loading plugins from remote repositories
  - **Plugin Configuration**: Enhanced configuration management for plugins
  - **Security Validation**: Built-in validation for plugin sources and configurations

### Changed

- **Tool Adapters**: All local tool adapters now use the new path utilities and loop protection
- **Error Handling**: Improved error messages with more context and actionable feedback
- **CLI Experience**: Enhanced command-line interface with better validation and feedback
- **Configuration**: Updated configuration system to support new security features

### Security

- **Loop Protection**: Prevents denial-of-service attacks through excessive file operations
- **Path Traversal**: Enhanced protection against directory traversal attacks
- **Input Sanitization**: All user inputs are properly sanitized before processing

### Developer Experience

- **Testing**: Added comprehensive test suite for loop protection and path utilities
- **Documentation**: Updated all documentation to reflect new security features
- **Examples**: Added example usage patterns for safe file operations

### Migration Guide

For users upgrading from previous versions:

1. **Configuration**: No breaking changes to existing configuration
2. **Backward Compatibility**: All existing commands and workflows continue to work
3. **New Features**: Loop protection is enabled by default for all local tools
4. **Path Handling**: Tilde expansion works automatically in all file paths

---

## [2.20.0] - 2025-08-10

### Added

- **Mistral AI Provider**: Added complete support for Mistral AI models
  - **General Purpose Models**:
    - `mistral-large-latest`: 128k context, most capable model (default)
    - `mistral-medium-latest`: 32k context, balanced performance
    - `mistral-small-latest`: 32k context, compact and efficient
  - **Code-Focused Models**:
    - `codestral-latest`: 256k context, specialized for code generation
    - `codestral-2405`: Previous version of code-focused model
  - **Development-Focused Models**:
    - `devstral-small-latest`: 128k context, optimized for agentic tool use
    - `devstral-medium-latest`: 128k context, enhanced agentic capabilities
- **Mistral Setup Guide**: Comprehensive documentation for Mistral AI integration
- **Tool Support**: Full tool/function calling support across all Mistral models
- **API Integration**: Uses OpenAI-compatible API format via Mistral's La Plateforme

## [2.19.0] - 2025-08-08

### Added

- **Alibaba Cloud Provider**: Added support for new Qwen3 1M context models
  - `qwen3-235b-a22b-thinking-2507`: 1M context thinking model
  - `qwen3-235b-a22b-instruct-2507`: 1M context instruct model
  - `qwen3-30b-a3b-thinking-2507`: 1M context thinking model
  - `qwen3-30b-a3b-instruct-2507`: 1M context instruct model
- **Thinking Mode Support**: Added thinking mode indicators (📖) for models that support chain-of-thought reasoning
- **Default Model Highlighting**: Added star (⭐) indicators to highlight default models in provider listings
- **Provider Connectivity Testing**: Added `--ping` flag to test connectivity with all providers when used with `--list-providers`
- **Enhanced Model Display**: Improved model listing with better formatting of context sizes and response limits

### Changed

- **Alibaba Cloud Provider**: Updated default model from `qwen3-coder-plus` to `qwen3-235b-a22b-instruct-2507` (129k context)
- **Model Information**: Added thinking mode support tracking in LLMModelInfo class
- **Documentation**: Updated Alibaba setup guide with comprehensive configuration instructions

## [2.18.0] - 2025-08-07

### Added

- Added OpenAI GPT-5 models (gpt-5, gpt-5-mini, gpt-5-nano) and set default model to gpt-5
- Chat session: improved backend hostname detection
- Cleaned up test file

## [2.17.0] - 2025-08-05

### Added

- **New Provider Support**
  - **Cerebras Provider**: Added complete support for Cerebras with qwen-3-coder-480b model
    - qwen-3-coder-480b: 32k context, reasoning-focused model with function calling support

- **Enhanced UX**
  - Improved error handling for invalid provider names in set-api-key command
  - Better error messages when provider is not found

### Changed

- **Provider Improvements**
  - Updated Alibaba endpoint to international URL for better global access
  - Simplified region display to 2-letter codes for cleaner output
  - Improved driver listing and region display functionality

- **Zero Mode Enhancement**
  - Zero mode now properly disables system prompt and tools for minimal interaction

### Fixed

- **Bug Fixes**
  - Added missing tools adapter to Cerebras provider
  - Improved error handling for invalid provider names in set-api-key command

## [2.16.0] - 2025-01-08

### Added

- **New CLI Features**
  - `--developer` flag: Start directly with Python developer profile without manual selection
  - `--multi` option: Enable default multiline input in chat mode
  - `--list-drivers` command: List available LLM drivers and their dependencies
  - `--list-providers-region` command: Show providers with region information

- **New Providers**
  - **Z.AI Provider**: Complete support for Z.AI with GLM-4.5, GLM-4, and GLM-4V models
    - GLM-4.5: 128k context with thinking support for advanced reasoning
    - GLM-4: General-purpose model with 128k context
    - GLM-4V: Vision model for image understanding with 128k context
  - **Alibaba Cloud Provider**: Support for Qwen models including qwen-turbo, qwen-plus, qwen-max, and qwen3-coder-plus

- **Enhanced UX**
  - Model information display now includes backend hostname in both chat and single-shot modes
  - Improved region management with geolocation utilities
  - Enhanced error handling for missing API keys and dependencies

### Changed

- **Provider Improvements**
  - Updated Z.AI provider to use official SDK with improved model support
  - Changed default GLM model from air to regular version
  - Updated Alibaba endpoint to international URL for better global access
  - Simplified region display to 2-letter codes for cleaner output

- **Documentation**
  - Updated documentation URLs to use GitHub Pages default domain
  - Fixed documentation URL to docs.janito.dev
  - Enhanced provider documentation with new Z.AI and Alibaba Cloud details

### Fixed

- **Bug Fixes**
  - Fixed AttributeError when ZAIProvider API key is missing
  - Removed accidentally committed test files
  - Improved error handling and user experience in profile selection
  - Fixed various import order issues for better code organization

- **Code Quality**
  - Refactored provider registry for reduced complexity
  - Improved CLI argument handling and validation
  - Enhanced terminal output styling and formatting

### Security

- **Enhanced Security**
  - Improved privilege checking and status display in chat sessions
  - Enhanced error handling for missing dependencies and API keys
  - Better validation of provider configurations

### Technical Improvements

- **Architecture**
  - Refactored core CLI and runner modules for better maintainability
  - Improved prompt handling and streamlined main CLI logic
  - Enhanced provider registry with new visual indicators
  - Better separation of concerns in driver and provider implementations

- **Performance**
  - Optimized model information retrieval
  - Improved startup performance with better configuration handling
  - Enhanced memory usage in chat sessions

### Developer Experience

- **Testing**
  - Added comprehensive tests for new CLI commands
  - Improved test coverage for provider configurations
  - Enhanced error handling in test scenarios

- **Documentation**
  - Updated all provider documentation with new features
  - Added comprehensive setup guides for new providers
  - Improved CLI usage examples and syntax highlighting

## [2.15.0] - 2025-08-05

## [2.16.0] - 2025-01-08

### Added

- Added `--developer` CLI flag to start with the Python developer profile without manual profile selection
- Added `--list-drivers` CLI command to list available LLM drivers and their dependencies
- Added `--multi` CLI option for default multiline input in chat mode
- Enhanced model information display with backend hostname in both chat and single-shot modes

### Changed

- Updated Z.AI provider to use official SDK with improved model support
- Changed default GLM model from air to regular version
- Updated documentation URLs to use GitHub Pages default domain

### Fixed

- Fixed AttributeError when ZAIProvider API key is missing
- Removed accidentally committed test files
- Improved error handling and user experience in profile selection

### Security

- Enhanced privilege checking and status display in chat sessions

## [2.15.0] - 2025-08-05

### Added

- **Z.AI Provider**: Added complete support for Z.AI with GLM-4.5, GLM-4, and GLM-4V models
  - GLM-4.5: 128k context with thinking support for advanced reasoning
  - GLM-4: General-purpose model with 128k context
  - GLM-4V: Vision model for image understanding with 128k context
- **Alibaba Cloud Provider**: Added support for Alibaba Cloud's Qwen models
  - qwen-turbo, qwen-plus, qwen-max, and qwen3-coder-plus models
- Updated supported providers documentation to include new Z.AI and Alibaba Cloud providers

### Changed

- Enhanced provider registry with new visual indicators and improved model listing
- Updated documentation to reflect new provider additions and model availability

### Removed

- Removed deprecated PROVIDERS.md file from janito/docs (content merged into supported-providers-models.md)

## [2.9.0] - 2025-07-16
### Added
- Added new `kimi-k2-turbo-preview` model to Moonshot provider
- Added visual indicators for default models in provider registry with star icons

### Changed
- Updated default Moonshot model from `kimi-k2-0711-preview` to `kimi-k2-turbo-preview`
- Updated all documentation to reflect new Moonshot model names and recommendations
- Updated project URLs, author email, and documentation for migration to ikignosis organization
- Updated repository links in documentation and configuration files to point to ikignosis GitHub organization
- Changed maintainer email in provider modules to janito@ikignosis.org
- Updated homepage and repo_url in pyproject.toml and mkdocs.yml to new organization URLs

### Fixed
- Fixed duplicate entries in supported providers documentation
- Fixed formatting in CLI command and privilege status modules

## [2.8.0] - 2025-07-16
### Added
- **Parallel tool calls**: Enabled for OpenAI provider when tools are available.
- **No-tools mode**: New CLI option to disable all tool usage.
- **Disabled tools functionality**: Support for selectively disabling specific tools.

### Changed
- **Configuration system**: Simplified by removing provider-specific settings.
- **Max wait time**: Increased from 300s to 600s in LLMAgent for better handling of long-running operations.
- **Custom system prompt UX**: Improved profile selection flow and user experience.
- **OpenAI dependency**: Updated to require openai>=1.68.0.
- **Code formatting**: Applied black formatting across the codebase.

### Removed
- **MistralAI provider**: Completely removed from the codebase.
- **Provider-specific settings**: Simplified configuration system.

### Documentation
- Updated Moonshot setup guide with platform.moonshot.ai domain.
- Improved CLI usage documentation and fixed syntax highlighting.
- Removed broken references to model_info.py files in supported-providers-models.md.
- Added comprehensive documentation updates across the project.

## [2.5.0] - 2025-07-01
### Added
- Show working directory in chat mode startup message.
- Bang (`!`) shell command handler for direct shell access from the chat interface.
- Elapsed time reporting to token usage summary and improved terminal output styling.
- CLI support for reading prompt from stdin and suppressing token usage summary in non-interactive mode.

### Changed
- Import `os` in help command handler for future extensibility.
- Refactored `ChatSession._chat_loop` to reduce complexity by extracting command and prompt handling methods.
- Refactored profile selection, removed `ProfileShellHandler`, and improved terminal reporter output for STDOUT/STDERR.
- Refactored to remove `exec_enabled` argument from agent and CLI setup; now uses `args.exec` directly.
- Improved terminal output: added `delete_current_line` to `RichTerminalReporter` for cleaner UI.
- Refactored and cleaned up: removed redundant import of `handle_command`, removed backup, structure, and test strategy files, and added `.vscode/settings.json` for VSCode excludes.

### Removed
- MistralAI provider and driver references and related files.
- Conversation history persistence and updated input history path.

### Documentation
- Removed inline web file viewer documentation from `README.md` for clarity and focus on core options.

## [2.4.0]

### Changed
- Refactored tool permission management: migrated to a permission-based model (read/write/execute), updated CLI and docs, removed legacy execution toggling.
- Enhanced tool permissions: tools are now grouped by permission, config supports tool_permissions, ask_user is read-only, and permissions are applied at startup.
- Refined permission and tool output messages in shell commands; improved tool listing by permission class in tools.py.
- Refactored agent and prompt handler setup, improved model switching, and enhanced user interrupt handling. Includes new /model shell command and fixes for provider registry ASCII fallback.
- Refactored agent system prompt and permissions logic, switched to profile-based template selection, removed unused templates, and added --profile CLI support.
- Refactored chat mode startup messages and permission reset handling for improved clarity.
- Refactored ChatSession and ChatShellState: removed allow_execution logic and related assignments, use exec_enabled directly for execution control.
- Refactored tool system to use latest git tag for version detection in release script.
- Refined release script to recommend creating a new git tag if version exists on PyPI.
- Removed termweb: web file viewer and related CLI/editor features, updated docs and config accordingly.
- Removed temporary file x.txt.
- Restored tool permissions to CLI defaults on /restart; store and retrieve default tool permissions in AllowedPermissionsState. Runner now sets and saves default permissions for restoration. Updated conversation_restart to restore or fallback to all-off permissions.
- Updated disabled execution tools message for clarity.
- Docs and UX: clarified permissions (read/write/exec), added profiles doc links, and removed localhost references from UI/toolbar.

### Added
- Agent/driver: drain driver's input queue before sending new messages in chat() to prevent stale DriverInput processing.

### Fixed
- Ensure tools adapter is always available in provider classes, even if driver is missing. Prevents AttributeError in generic code paths relying on execute_tool().

## [2.3.1] - 2025-06-25
### Changed
- Bumped version to 2.3.1 in `version.py`, `pyproject.toml`, and `__init__.py`.

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
# Changelog v2.23.0

## [2.23.0] - 2025-08-14

### Added

- **Remote Plugin Repository Support**: Added comprehensive support for loading plugins from the official `ikignosis/janito-plugins` repository
  - **Automatic Discovery**: Plugins can be automatically discovered and loaded from remote GitHub repository
  - **Configuration Management**: New configuration options for remote plugin management
  - **Security Features**: Built-in verification and sandboxing for remote plugins
  - **Update Mechanism**: Automatic and manual update capabilities for remote plugins

- **Plugin System Enhancements**:
  - **Plugin Categories**: Official and community plugin categorization
  - **Configuration Schemas**: JSON schema validation for plugin configuration
  - **Hot Loading**: Dynamic plugin loading/unloading without restart
  - **CLI Integration**: New commands for plugin management (`--list-remote-plugins`, `--update-remote-plugins`)

- **Documentation**: Comprehensive guides for remote plugin usage
  - [Remote Plugins Guide](../guides/remote-plugins.md) - Complete documentation for remote plugin usage
  - Updated [Plugin System Guide](../guides/plugins.md) with remote plugin integration
  - Enhanced [README-PLUGINS.md](../../README-PLUGINS.md) with remote repository references

### Changed

- **Plugin Discovery**: Enhanced plugin discovery system to support both local and remote sources
- **Configuration Format**: Extended `janito.json` to support remote plugin configuration
- **CLI Interface**: Added new plugin management commands and improved existing ones

### Security

- **Repository Verification**: Added verification for remote plugin sources
- **Access Control**: Implemented proper access controls for remote plugin loading
- **Configuration Validation**: Enhanced validation for plugin configuration parameters

### Developer Experience

- **Plugin Templates**: Added example plugin structure in `plugins/example_plugin.py`
- **Testing Framework**: Comprehensive test suite for plugin system in `tests/test_plugin_system.py`
- **Documentation**: Detailed API documentation and usage examples

### Migration Guide

For users upgrading from previous versions:

1. **Configuration Update**: Add remote plugin configuration to `janito.json`:
   ```json
   {
     "plugins": {
       "remote": {
         "enabled": true,
         "repository": "https://github.com/ikignosis/janito-plugins.git"
       }
     }
   }
   ```

2. **Plugin Discovery**: Existing local plugins continue to work unchanged
3. **CLI Commands**: New commands are backward compatible with existing usage

### Contributors

- Enhanced plugin system architecture
- Added remote repository integration
- Improved documentation and examples
- Strengthened security and validation features

---

## [3.1.0] - 2025-08-23

### Added

- **Enter Key Cancellation Support for Chat Mode**: Revolutionary usability improvement for interactive chat sessions
  - **Instant Request Cancellation**: Press **Enter key** at any time to immediately cancel current LLM operations
  - **Global Cancellation Manager**: Robust cross-component cancellation system spanning agent, driver, and prompt handler
  - **User Feedback**: Clear visual confirmation with red "Request cancelled by Enter key" message
  - **Clean State Management**: Automatic cleanup of cancellation state after request completion
  - **Thread-Safe Implementation**: Safe cancellation across multiple threads and async operations

### Technical Implementation

- **Global Cancellation Manager**: New `janito.llm.cancellation_manager` module provides centralized cancellation handling
- **Key Binding Integration**: Enhanced chat mode with dedicated Enter key handling for cancellation
- **Cross-Component Support**: Cancellation signals properly propagate through entire application stack
- **Backward Compatible**: All existing functionality preserved, cancellation is additive feature

### Developer Experience

- **Extensible Architecture**: Cancellation system designed for future integration with other components
- **Clean API**: Simple interface for starting, cancelling, and clearing requests across application
- **Comprehensive Testing**: Full test coverage for cancellation scenarios and edge cases

### Documentation

- Updated CLI options documentation with new cancellation behavior
- Enhanced chat mode guides with cancellation instructions
- Added troubleshooting section for long-running requests
- New dedicated changelog: [CHANGELOG_3.1.0.md](../changelogs/CHANGELOG_3.1.0.md)

---

**Full Changelog**: https://github.com/ikignosis/janito/compare/v2.22.0...v2.23.0