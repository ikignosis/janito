# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaompinto/janito/compare/v4.26.0...HEAD)

Changes since `v4.26.0` (2026-08-17).

### Changed

- The OneDrive functionality (tools, system prompt, authentication) was
  extracted from the core into the `janito-onedrive-plugin` plugin.  The
  `--onedrive`, `--onedrive-auth`, `--onedrive-logout` and `--onedrive-status`
  CLI flags are removed; use `--plugin ../plugins/janito-onedrive-plugin`
  (or install it to `~/.janito/plugins`).  When the plugin loads and the
  `azure_client_id` secret is configured, it runs the device code
  authentication flow automatically — set the secret with
  `janito --set-secret azure_client_id=your-client-id`, then restart janito.
  The `/onedrive` shell command provides `logout` and `status` subcommands
  (authentication is automatic, so there is no `auth` subcommand).  The
  OneDrive docs moved into the plugin's README.
- The version banner (`Janito x.y.z - Working at <cwd>`) is now printed
  before any plugin loading messages at startup, instead of only with the
  full-privileges warning.
- A plugin whose `on_start()` hook reports an error (e.g. the gmail plugin
  when the required secrets are missing) now **fails to load**: its tools,
  commands and system-prompt section are no longer registered.  Previously
  the error was recorded but the plugin's content was still activated.
- Plugin loading now prints `Loading plugin <name>` with `end=""` and then
  prints ` OK` or ` FAILED: <reason>` on completion, e.g.
  `Loading plugin janito-gmail-plugin OK` or
  `Loading plugin janito-gmail-plugin FAILED: missing required secret: gmail_username`.
- `--plugin` pointing to a missing directory (or a directory without an
  `__init__.py`) now reports a clear error
  (`plugin directory not found: <path> (check the path passed to --plugin)`
  / `plugin directory has no __init__.py: <path>`) instead of a confusing
  `No module named ...` from the import.
