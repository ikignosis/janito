# Changelog v2.27.0

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

### Developer Experience

- **CLI Usability**: 
  - Streamlined one-shot mode with convenient prefix commands
  - Consistent behavior between interactive and non-interactive modes
  - Clear documentation for new features

### Technical Details

- **Implementation**: Enhanced CLI argument parsing to support `/rwx` prefix
- **Integration**: Full integration with existing permission system
- **Compatibility**: Backward compatible with existing CLI flags and commands

### Migration Guide

For users upgrading from v2.26.0:

1. **No Breaking Changes**: All existing functionality remains unchanged
2. **New Prefix**: Use `/rwx "prompt"` for one-shot mode with all permissions
3. **Existing Flags**: `-r -w -x` flags continue to work as before
4. **fetch_url Tool**: Enhanced session support is automatic, no configuration needed

### Contributors

- Added convenient one-shot mode prefix for improved CLI experience
- Enhanced web fetching capabilities with browser-like session support
- Improved documentation and parameter descriptions
- Fixed documentation inconsistencies

---

**Full Changelog**: https://github.com/ikignosis/janito/compare/v2.26.0...v2.27.0