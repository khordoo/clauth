# Changelog

All notable changes to this project will be documented in this file.

## [0.1.4] - 2025-09-29
### Added
- Introduced UI helpers (`WizardScreen`, `Spinner`) for panel-based multi-step flows.
- Added a `clauth sm` shortcut for quick model switching and documented it across the CLI help and README.
- Embedded an animated CLI demo (`assets/demo/demo.gif`) to showcase the setup experience.

### Changed
- Relocated the destructive cleanup to `clauth config delete` while keeping the old `clauth delete` as a deprecated shim.
- Standardized Inquirer selection colours via a new theme token; removed redundant inline instructions.
- Restyled the delete command to show spinner-backed steps and a final summary card.
- CI now installs/builds with `uv` and coverage targets the installed package.

### Fixed
- Replaced remaining raw coloured console output with themed status/cards across helpers, launcher, and AWS utilities.

## [0.1.1] - 2025-09-28
### Added
- Expanded README installation instructions and project overview.
- Additional CLI help text for model management commands.

### Fixed
- Initial grooming of AWS credential handling and configuration validations.

## [0.1.0] - 2025-09-28
### Added
- Initial public release with `clauth init`, `clauth model`, and configuration management commands.
- Automated AWS SSO setup, Bedrock model discovery, and Claude Code launch integration.

[0.1.4]: https://github.com/khordoo/clauth/releases/tag/v0.1.4
[0.1.1]: https://github.com/khordoo/clauth/releases/tag/v0.1.1
[0.1.0]: https://github.com/khordoo/clauth/releases/tag/v0.1.0
