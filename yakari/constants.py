import os
from pathlib import Path

# Menu constants
DEFAULT_ARGUMENT_FIELDS = {"separator": "space", "multi_style": ","}

DEFAULT_YAKARI_HOME = Path(os.environ["HOME"]) / ".config" / "yakari"
YAKARI_HOME = Path(os.environ.get("YAKARI_HOME", DEFAULT_YAKARI_HOME))

MENUS_DIR = "menus"
TEMPORARY_MENUS_DIR = "temporary_menus"
HISTORY_FILENAME = "history"
HISTORY_FILE = YAKARI_HOME / HISTORY_FILENAME

REMOTE_DEFAULT = (
    "https://raw.githubusercontent.com/vlandeiro/yakari-menus/refs/heads/main"
)

HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
