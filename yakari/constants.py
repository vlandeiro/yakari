import os
from pathlib import Path


DEFAULT_YAKARI_HOME = Path(os.environ["HOME"]) / ".config" / "yakari"
YAKARI_HOME = Path(os.environ.get("YAKARI_HOME", DEFAULT_YAKARI_HOME))
CONFIGURATIONS_DIR = "configurations"
HISTORY_DIR = "history"
