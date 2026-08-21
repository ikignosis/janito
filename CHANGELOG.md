# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaompinto/janito/compare/v4.29.0...HEAD)

Changes since `v4.29.0` (2026-08-20).

### Added

- Interactive chat now prints the resolved provider, model and API type
  (colorized) before starting the session, annotated with `(server-side)` or
  `(client-side)` depending on the `responses-in-server` ("keep in server")
  config.
