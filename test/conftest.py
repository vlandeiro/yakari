import pytest
from pathlib import Path
from yakari.types import Menu
from yakari.app import YakariApp


@pytest.fixture
def demo_app():
    """Fixture providing a configured YakariApp instance."""
    # Get the absolute path to the demos.toml file
    yakari_root = Path(__file__).parent.parent
    demo_file = yakari_root / "menus" / "demo.toml"

    menu = Menu.from_toml(demo_file)
    app = YakariApp(menu, dry_run=True)
    return app
