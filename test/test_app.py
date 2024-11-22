import pytest

from yakari.app import YakariApp
from yakari.types import (
    ChoiceArgument,
    Command,
    Deferred,
    FlagArgument,
    Menu,
    ValueArgument,
)

OPTIONAL_ARGUMENTS = Deferred(varname="optional_arguments")


@pytest.fixture
def mock_app():
    """Fixture providing a configured YakariApp instance."""
    menu = Menu(
        name="Test Menu",
        commands={
            "t": Command(
                name="Test Command",
                description="Test description",
                template=["mock_app", OPTIONAL_ARGUMENTS],
            ),
        },
        arguments={
            "-f": FlagArgument(flag="--flag", description="Test flag"),
            "-v": ValueArgument(name="--value", description="Test value"),
            "-c": ChoiceArgument(
                name="--choice", description="Test choice", choices=["a", "b", "c"]
            ),
            "--long-flag": FlagArgument(
                flag="--long-flag", description="Another test flag"
            ),
        },
    )
    app = YakariApp(menu)
    return app


@pytest.mark.asyncio
async def test_argument_inputs(mock_app):
    """Test handling of argument input."""
    async with mock_app.run_test() as pilot:
        # await pilot.pause()

        # Test flag argument
        await pilot.press(*"-f")

        # Test value argument
        await pilot.press(*"-v")
        await pilot.press(*"foo")
        await pilot.press("enter")

        # Test choice argument
        await pilot.press(*"-c")
        await pilot.press("down", "enter")

        # Call the command
        await pilot.press("t")

        assert mock_app.command == ["mock_app", "--flag", "--value foo", "--choice b"]


@pytest.mark.asyncio
async def test_input_clearing_with_backspace(mock_app):
    """Test clearing input field."""
    async with mock_app.run_test() as pilot:
        # await pilot.pause()
        screen = pilot.app.screen

        # Type something
        await pilot.press(*"--long")
        assert screen.cur_input == "--long"

        # Clear input
        await pilot.press("backspace")
        assert screen.cur_input == "--lon"
        await pilot.press(*["backspace"] * 5)
        assert screen.cur_input == ""


@pytest.mark.asyncio
async def test_input_autoclearing(mock_app):
    """Test auto-clearing input field when there are no match."""
    async with mock_app.run_test() as pilot:
        # await pilot.pause()
        screen = pilot.app.screen

        # Type something
        await pilot.press(*"--long")
        assert screen.cur_input == "--long"

        # Auto-clear input because there are no matching entries
        await pilot.press("e")
        assert screen.cur_input == ""


@pytest.mark.asyncio
async def test_input_tab_completion(mock_app):
    """Test clearing input field."""
    async with mock_app.run_test() as pilot:
        # await pilot.pause()
        screen = pilot.app.screen

        # Type something
        await pilot.press(*"--long")
        assert screen.cur_input == "--long"

        # Complete input on tab press and activate flag
        await pilot.press("tab")
        assert screen.cur_input == ""
        assert mock_app.menu.arguments["--long-flag"].enabled
