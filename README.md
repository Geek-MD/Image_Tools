[![Geek-MD - Image Tools](https://img.shields.io/static/v1?label=Geek-MD&message=Image%20Tools&color=blue&logo=github)](https://github.com/Geek-MD/Image_Tools)
[![Stars](https://img.shields.io/github/stars/Geek-MD/Image_Tools?style=social)](https://github.com/Geek-MD/Image_Tools)
[![Forks](https://img.shields.io/github/forks/Geek-MD/Image_Tools?style=social)](https://github.com/Geek-MD/Image_Tools)

[![GitHub Release](https://img.shields.io/github/release/Geek-MD/Image_Tools?include_prereleases&sort=semver&color=blue)](https://github.com/Geek-MD/Image_Tools/releases)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://github.com/Geek-MD/Image_Tools/blob/main/LICENSE)
[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom%20Repository-blue)](https://hacs.xyz/)

[![Ruff + Mypy + Hassfest](https://github.com/Geek-MD/Image_Tools/actions/workflows/validate.yml/badge.svg)](https://github.com/Geek-MD/Image_Tools/actions/workflows/validate.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

<img width="200" height="200" alt="image" src="https://github.com/Geek-MD/Image_Tools/blob/main/custom_components/image_tools/brand/icon.png?raw=true" />

# Image Tools

Home Assistant custom integration that exposes services for resizing images,
adjusting their aspect ratio, and converting between image formats supported by
Home Assistant (PNG, JPG, WebP, GIF, BMP, TIFF).

## Features

- **`resize_image` service** — resize an image to a target width and/or height,
  with optional aspect-ratio control (crop, letterbox, or stretch).
- **`convert_image` service** — convert an image to any format supported by HA.
- **Status sensor** — `sensor.image_tools_status` reports `working` or `idle` so
  automations can react to processing activity. Attributes include the last job
  result, operation type, timestamp, and the list of processes performed.
- **Automation-friendly events** — `image_tools_image_processing_finished` is fired
  after every service call and can be used directly as an automation trigger.
- Optional **service responses** — both services can return structured data via
  `response_variable` in scripts.
- Easy **UI setup** through Settings → Devices & Services.
- **HACS** installable as a custom repository.

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance.
2. Click on **Integrations**.
3. Click the three dots in the top-right corner and select **Custom repositories**.
4. Add the repository URL: `https://github.com/Geek-MD/Image_Tools`
5. Select **Integration** as the category and click **Add**.
6. Search for **Image Tools** in HACS and click **Download**.
7. Restart Home Assistant.
8. Go to **Settings → Devices & Services**.
9. Click **+ Add Integration** and search for **Image Tools**.
10. Follow the configuration steps.

### Manual Installation

1. Copy the `custom_components/image_tools` directory into your Home Assistant
   `custom_components` folder.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services**.
4. Click **+ Add Integration** and search for **Image Tools**.
5. Follow the configuration steps.

## Configuration

Image Tools can only be configured **once** per Home Assistant instance.

During setup you will be asked for an optional **Work Directory** — a reference path
shown in the UI. All service calls specify full file paths explicitly, so this field
is informational only.

## Services

### `image_tools.resize_image`

Resize an image to specific dimensions. You can also adjust the aspect ratio before
resizing.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `input_path` | ✅ | — | Full path to the source image file. |
| `output_path` | ❌ | auto | Full path for the output file. Auto-generated with `_resized` suffix if omitted and `overwrite` is false. |
| `overwrite` | ❌ | `false` | Overwrite the original file. |
| `width` | ❌ | — | Target width in pixels. |
| `height` | ❌ | — | Target height in pixels. |
| `keep_aspect_ratio` | ❌ | `true` | Preserve the original aspect ratio. |
| `target_aspect_ratio` | ❌ | — | Desired aspect ratio as a decimal (e.g. `1.777` for 16:9). Applied before resizing. |
| `aspect_mode` | ❌ | `crop` | How to apply `target_aspect_ratio`: `crop` (centre-crop), `letterbox` (add black bars), or `stretch` (distort). |

> **Note:** At least one of `width`, `height`, or `target_aspect_ratio` must be
> provided.

**Example — resize to 1920×1080:**

```yaml
action: image_tools.resize_image
data:
  input_path: "/media/photos/photo.jpg"
  output_path: "/media/photos/photo_1080p.jpg"
  width: 1920
  height: 1080
```

**Example — crop to 16:9 then scale to 1280 wide:**

```yaml
action: image_tools.resize_image
data:
  input_path: "/media/photos/portrait.jpg"
  output_path: "/media/photos/portrait_landscape.jpg"
  width: 1280
  target_aspect_ratio: 1.777
  aspect_mode: "crop"
```

---

### `image_tools.convert_image`

Convert an image to a different file format.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `input_path` | ✅ | — | Full path to the source image file. |
| `output_path` | ❌ | auto | Full path for the output file. Auto-generated by changing the extension if omitted and `overwrite` is false. |
| `overwrite` | ❌ | `false` | Overwrite the original file. |
| `output_format` | ✅ | — | Target format: `png`, `jpg`, `jpeg`, `webp`, `gif`, `bmp`, `tiff`, or `tif`. |

**Example — convert PNG to WebP:**

```yaml
action: image_tools.convert_image
data:
  input_path: "/media/photos/photo.png"
  output_path: "/media/photos/photo.webp"
  output_format: "webp"
```

**Example — automation that converts every new PNG in a watched folder:**

```yaml
automation:
  - alias: "Convert new PNGs to WebP"
    trigger:
      - platform: event
        event_type: folder_watcher
        event_data:
          event_type: created
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.file.endswith('.png') }}"
    action:
      - action: image_tools.convert_image
        data:
          input_path: "{{ trigger.event.data.path }}"
          output_format: "webp"
```

## Entities

### Status Sensor — `sensor.image_tools_status`

| State | Meaning |
|-------|---------|
| `working` | A service call is currently processing an image. |
| `idle` | No active processing; the integration is waiting for work. |

**Attributes:**

| Attribute | Description |
|-----------|-------------|
| `last_job` | Result of the last job: `success` or `failed`. |
| `last_operation` | Operation that was last started: `resize` or `convert`. |
| `timestamp` | ISO 8601 timestamp of the last state change (server local time). |
| `processes` | List of operations completed in the last job. |

**Example automation — notify when processing is done:**

```yaml
automation:
  - alias: "Notify when image processing completes"
    trigger:
      - platform: state
        entity_id: sensor.image_tools_status
        from: "working"
        to: "idle"
    action:
      - action: notify.mobile_app
        data:
          title: "Image Processing Complete"
          message: >
            Result: {{ state_attr('sensor.image_tools_status', 'last_job') }}
            Operation: {{ state_attr('sensor.image_tools_status', 'last_operation') }}
```

## Events

Both services fire the `image_tools_image_processing_finished` event when they
complete (regardless of success or failure).

**Event data:**

| Field | Description |
|-------|-------------|
| `operation` | `resize` or `convert`. |
| `input_path` | Path to the source image. |
| `output_path` | Path to the output image (`null` on failure). |
| `output_format` | Target format (`convert` only). |
| `result` | `success` or `failed`. |
| `error` | Error message when `result` is `failed` (`null` otherwise). |

**Example automation — react to event:**

```yaml
automation:
  - alias: "Handle image processing failure"
    trigger:
      - platform: event
        event_type: image_tools_image_processing_finished
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.result == 'failed' }}"
    action:
      - action: notify.mobile_app
        data:
          title: "Image Processing Failed"
          message: >
            Operation: {{ trigger.event.data.operation }}
            File: {{ trigger.event.data.input_path }}
            Error: {{ trigger.event.data.error }}
```

## Service Lifecycle

Every service call follows this lifecycle to guarantee correct event and sensor ordering:

1. **Process image** — the image is processed (resize / convert).
2. **Fire event** — `image_tools_image_processing_finished` is fired so automations
   can react before any state update.
3. **Update sensor** — the status sensor transitions to `idle` with the job result.

## Requirements

- Home Assistant 2023.1.0 or newer.
- [Pillow](https://pillow.readthedocs.io/) — already bundled with Home Assistant core.

---

<div align="center">

💻 **Proudly developed with GitHub Copilot** 🚀

</div>
