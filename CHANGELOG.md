# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.6.0] - 2025-09-04

### Added

- **Blocked Sites Functionality**: Added comprehensive blocked sites management to prevent access to known problematic sites

  - Created `BlockedSitesManager` class to handle blocked sites checking
  - Added `janito/data/blocked.txt` with list of sites requiring authentication/paywalls
  - Integrated blocked sites check into `fetch_url` tool
  - Sites blocked include: Reuters, WSJ, NYT, academic databases, social media platforms, streaming services, and other paywall-protected content

### Security

- Enhanced URL filtering with dual-layer protection (blocked sites + whitelist)
- Added domain-based blocking for subdomains of blocked sites
- Improved error messaging for blocked sites

### Technical

- Added package data inclusion for `blocked.txt` in distribution
- Created test script `test_blocked_sites.py` for verification
- Updated fetch_url tool to check blocked sites before whitelist

## [3.5.1] - 2024-08-29

### Fixed
- Bug fixes and performance improvements

## [3.5.0] - 2024-08-29

### Added
- Initial release with core functionality