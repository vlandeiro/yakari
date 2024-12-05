import os
from pathlib import Path

# Menu constants
DEFAULT_ARGUMENT_FIELDS = {
    "separator": "space",
    "multi_style": ","
}

DEFAULT_YAKARI_HOME = Path(os.environ["HOME"]) / ".config" / "yakari"
YAKARI_HOME = Path(os.environ.get("YAKARI_HOME", DEFAULT_YAKARI_HOME))
CONFIGURATIONS_DIR = "configurations"
HISTORY_FILENAME = "history"
HISTORY_FILE = YAKARI_HOME / HISTORY_FILENAME

HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
