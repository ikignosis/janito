# Changelog v3.5.0

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

### Documentation Updates

- **Comprehensive Guides**: Updated all documentation for v3.5.0 features
- **Setup Instructions**: Enhanced setup guides with new social media integration
- **API Documentation**: Updated API references with new timer and preview features
- **Migration Guide**: Added migration notes for users upgrading from previous versions

### Developer Experience

- **Testing**: Enhanced test coverage for new features
- **Examples**: Added usage examples for live timer and social media features
- **Debugging**: Improved debugging capabilities with cleaner terminal output

---

**Full Changelog**: https://github.com/ikignosis/janito/compare/v3.4.0...v3.5.0