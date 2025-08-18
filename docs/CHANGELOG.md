# Changelog

All notable changes to Janito will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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