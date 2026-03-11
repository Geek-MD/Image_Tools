"""Constants for the Image Tools integration."""

DOMAIN = "image_tools"
CONF_WORK_DIR = "work_dir"
DEFAULT_WORK_DIR = ""

# Sensor states
STATE_WORKING = "working"
STATE_IDLE = "idle"

# Supported image formats (Pillow format id)
SUPPORTED_FORMATS: dict[str, str] = {
    "png": "PNG",
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "webp": "WEBP",
    "gif": "GIF",
    "bmp": "BMP",
    "tiff": "TIFF",
    "tif": "TIFF",
}

# Valid output formats for the service (user-facing)
VALID_OUTPUT_FORMATS = list(SUPPORTED_FORMATS.keys())

# Aspect ratio modes
ASPECT_MODE_CROP = "crop"
ASPECT_MODE_LETTERBOX = "letterbox"
ASPECT_MODE_STRETCH = "stretch"
VALID_ASPECT_MODES = [ASPECT_MODE_CROP, ASPECT_MODE_LETTERBOX, ASPECT_MODE_STRETCH]
