# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-11

### Added

- **Initial release** of the Image Tools Home Assistant custom integration.
- **`image_tools.resize_image` service** — resize images to specific dimensions with
  optional aspect-ratio control (crop, letterbox, or stretch modes).
- **`image_tools.convert_image` service** — convert images between all formats
  supported by Home Assistant (PNG, JPG/JPEG, WebP, GIF, BMP, TIFF).
- **Status sensor** (`sensor.image_tools_status`) — exposes `working` / `idle` states
  so automations can react to processing activity. Includes attributes:
  `last_job` (success/failed), `last_operation` (resize/convert), `timestamp`,
  and `processes` (list of operations performed).
- **`image_tools_image_processing_finished` event** — fired after every service call
  with `operation`, `input_path`, `output_path`, `result`, and `error` fields.
  Can be used directly as an automation trigger.
- **Config flow** — UI-based setup via Settings → Devices & Services with an optional
  work directory field.
- **Service responses** — both services support optional return responses (usable in
  scripts via `response_variable`).
- **HACS support** — the integration can be installed from HACS as a custom repository.
- **CI workflow** (`.github/workflows/validate.yml`) — runs Ruff, Mypy, and Hassfest
  on every push and pull request.
- **English and Spanish translations** for the config flow and sensor entity.
