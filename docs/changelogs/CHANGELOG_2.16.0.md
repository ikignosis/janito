# Changelog v2.16.0

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