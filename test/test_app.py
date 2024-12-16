import pytest


@pytest.mark.asyncio
async def test_flag_argument(demo_app):
    async with demo_app.run_test() as pilot:
        # await pilot.pause()

        # Test flag argument
        await pilot.press("a")
        await pilot.press(*"-f")
        await pilot.press("d")

        assert demo_app.command == [
            "echo",
            "--parent=100",
            "--flag",
            "--named-with-default=3",
        ]


@pytest.mark.asyncio
async def test_single_value_named_argument(demo_app):
    async with demo_app.run_test() as pilot:
        await pilot.press("a")
        await pilot.press(*"-n")
        await pilot.press(*"foo")
        await pilot.press("enter")
        await pilot.press("d")

        assert demo_app.command == [
            "echo",
            "--parent=100",
            "--named=foo",
            "--named-with-default=3",
        ]


@pytest.mark.asyncio
async def test_multiple_values_named_argument(demo_app):
    async with demo_app.run_test() as pilot:
        # go to the arguments menu
        await pilot.press("a")

        await pilot.press(*"--mn")
        # type foo
        await pilot.press(*"foo")
        await pilot.press("enter")
        # type bar
        await pilot.press(*"bar")
        await pilot.press("enter")
        # select the last suggestion
        await pilot.press("shift+tab")
        await pilot.press("up")
        await pilot.press("enter")
        await pilot.press("enter")

        # submit the selected values
        await pilot.press("enter")
        # run the echo command
        await pilot.press("d")

        assert demo_app.command == [
            "echo",
            "--parent=100",
            "--named-with-default=3",
            "--multi-named=foo",
            "--multi-named=bar",
            "--multi-named=peach",
        ]


@pytest.mark.asyncio
async def test_single_choice_argument(demo_app):
    async with demo_app.run_test() as pilot:
        await pilot.press("a")
        await pilot.press(*"-c")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.press("d")

        assert demo_app.command == [
            "echo",
            "--parent=100",
            "--named-with-default=3",
            "--single-choice=rust",
        ]


@pytest.mark.asyncio
async def test_multi_choice_argument(demo_app):
    async with demo_app.run_test() as pilot:
        await pilot.press("a")
        await pilot.press(*"--mc")
        # select "jazz"
        await pilot.press("space")
        # select "npr news"
        await pilot.press("down", "down", "space")

        await pilot.press("enter")
        await pilot.press("d")

        assert demo_app.command == [
            "echo",
            "--parent=100",
            "--named-with-default=3",
            "--multi-choice=jazz",
            "--multi-choice=npr news",
        ]
