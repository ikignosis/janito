# Changelog v2.26.0

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

### Developer Experience

- **Chat Mode Usability**: 
  - Seamless switching between security modes without restart
  - Clear visual indicators for current security state
  - Consistent behavior between CLI flags and shell commands

### Technical Details

- **Implementation**: New `UnrestrictedShellHandler` class in `janito.cli.chat_mode.shell.commands.unrestricted`
- **Integration**: Full integration with existing shell state management
- **Compatibility**: Backward compatible with existing `-u` CLI flag behavior

### Migration Guide

For users upgrading from v2.25.0:

1. **No Breaking Changes**: All existing functionality remains unchanged
2. **New Command**: Use `/unrestricted` in chat mode shell to toggle unrestricted mode
3. **CLI Flag**: The `-u` CLI flag continues to work as before
4. **Security**: Unrestricted mode is clearly indicated with red warning text

### Contributors

- Added unrestricted mode command for enhanced chat mode flexibility
- Improved security state management in shell commands
- Enhanced user feedback for security-sensitive operations

---

**Full Changelog**: https://github.com/ikignosis/janito/compare/v2.25.0...v2.26.0