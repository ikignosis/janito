# Changelog

All notable changes to Janito will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [3.5.0] - 2025-08-28

### Added

- **Live Timer Display**: Added real-time timer display while waiting for LLM responses
  - Shows elapsed time during LLM processing
  - Provides visual feedback for long-running requests
  - Clean, non-intrusive display in terminal interface

- **Social Media Integration**: Added comprehensive social media preview support
  - **LinkedIn Integration**: Custom preview images and meta tags for LinkedIn sharing
  - **Platform Support**: Enhanced meta tags for Twitter, Facebook, and other social platforms
  - **Professional Branding**: Consistent visual identity across social media platforms

- **Enhanced Documentation**: Major improvements to documentation system
  - **Navigation Features**: Added comprehensive navigation and search capabilities
  - **Google Integration**: Added Google site verification meta tag for better indexing
  - **Preview Tags**: Enhanced markdown extensions with preview tag support
  - **User Experience**: Improved documentation layout and accessibility

### Changed

- **Loop Protection Enhancement**: Relaxed create_file loop protection from 10 seconds to 1 hour per path
  - **Better User Experience**: Reduced false positives for legitimate rapid file creation
  - **Maintained Security**: Still prevents abuse while allowing normal development workflows
  - **Configurable**: Protection adapts to actual usage patterns

- **Terminal Output Cleanup**: Removed styling from stdout/stderr output in rich terminal reporter
  - **Cleaner Output**: Plain text output for better readability and copy-paste compatibility
  - **Tool Integration**: Improved compatibility with external tools and scripts
  - **Consistent Formatting**: Standardized output across all terminal environments

### Fixed

- **Documentation Corrections**: Fixed various documentation issues and broken links
- **Shell Command Fixes**: Updated documentation with correct shell commands and examples
- **Thin Client Description**: Restored accurate thin client documentation

### Technical Improvements

- **Code Quality**: Minor cleanups and structure improvements across CLI and plugins
- **Cancellation Handling**: Improved cancellation handling mechanisms
- **Provider Configuration**: Updated bindings and provider configurations for latest APIs
- **Working Directory**: Cleaned working directory before release for optimal distribution

## [3.0.0] - 2025-08-23

### Major Architecture Refactoring

#### Plugin System Overhaul
- **Complete plugin system redesign** with unified architecture
- **Consolidated core plugins** into cohesive `janito/plugins/` structure
- **Eliminated legacy loading mechanisms** (`core_loader.py`, `core_loader_fixed.py`, `base.py`)
- **Streamlined plugin discovery** with improved initialization process
- **Enhanced maintainability** through simplified plugin architecture

#### Removed Legacy Components
- Deleted deprecated plugin loading systems
- Removed redundant `plugins.txt` configuration file
- Eliminated duplicate tool adapter implementations
- Cleaned up temporary test files (`test_core_plugins*.py`)

#### Enhanced Plugin Organization
- **Unified plugin structure** with clear module hierarchy
- **Consolidated tool categories**:
  - Core system tools (file operations, system commands)
  - Development tools (Python execution, code analysis)
  - UI tools (user interaction, visualization)
  - Web tools (URL fetching, browser integration)
- **Improved plugin discovery** with automatic initialization

### Technical Improvements

#### Code Quality
- **Reduced complexity** through architectural simplification
- **Eliminated code duplication** across plugin implementations
- **Enhanced modularity** with clear separation of concerns
- **Improved testability** with focused plugin modules

#### Configuration Simplification
- **Streamlined plugin configuration** with unified settings
- **Simplified initialization process** for new plugins
- **Reduced configuration overhead** for plugin developers

### Breaking Changes

#### Plugin System
- **Legacy plugin loading mechanisms removed** - plugins must use new system
- **Plugin directory structure changed** - see updated documentation
- **Configuration format updated** - simplified plugin settings

#### Removed Files
- `plugins.txt` configuration file
- Legacy plugin loading modules
- Temporary test files
- Redundant tool adapter implementations

### Migration Guide

#### For Plugin Developers
1. **Update plugin structure** to match new unified architecture
2. **Migrate configuration** to new simplified format
3. **Test compatibility** with new plugin discovery system
4. **Review documentation** for updated development patterns

#### For Users
1. **Update configuration files** to use new plugin system
2. **Review plugin settings** for simplified format
3. **Test existing workflows** with new architecture

### Documentation Updates
- **Comprehensive plugin development guide** with updated patterns
- **Migration documentation** for legacy plugin system
- **Enhanced API reference** with new plugin interfaces

## [2.27.0] - 2025-08-22

### Removed

- **Breaking Change**: Removed `--role` argument and interactive profile selection
  - The `--role` argument has been completely removed from the CLI
  - Interactive profile selection has been removed from chat mode
  - Use `--profile <name>` or shorthand flags like `--developer` and `--market` instead
  - Default behavior now uses the Developer profile when no profile is specified

### Changed

- Updated documentation to reflect removal of role argument
- Added comprehensive profile documentation in `PROFILES.md`
- Simplified profile selection to use explicit flags only

## [Previous Versions]

### Added

- Initial support for profiles and roles
- Interactive profile selection in chat mode
- `--role` argument for specifying developer roles
- `--profile` argument for system prompt templates
- `--developer` and `--market` shorthand flags

### Available Profiles

- **Developer**: Optimized for software development tasks
- **Market Analyst**: Specialized for market analysis and business insights

### Supported Providers

- Moonshot AI (default)
- OpenAI
- Anthropic
- IBM WatsonX
- Google AI

---

For detailed information about profiles and their usage, see [PROFILES.md](PROFILES.md).