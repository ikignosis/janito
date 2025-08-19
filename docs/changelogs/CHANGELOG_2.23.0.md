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

**Full Changelog**: https://github.com/ikignosis/janito/compare/v2.22.0...v2.23.0