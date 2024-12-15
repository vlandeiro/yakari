import asyncio
from typing import List

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, RichLog


class CommandRunner(Widget):
    can_focus_children = True

    _process_running: reactive(bool) = reactive(False, recompose=True)

    BINDINGS = [
        ("ctrl+q", "terminate_subprocess", "terminate command"),
    ]

    def __init__(self):
        super().__init__()
        self.log_widget = RichLog(highlight=True, wrap=True, auto_scroll=True)
        self.log_widget.can_focus = False
        self.user_input = Input(placeholder="Interact with your command")
        self.subprocess: asyncio.subprocess.Process | None = None
        self.extra_stdout: bytes = b""
        self.extra_stdout_lock = asyncio.Lock()

    @work
    async def start_subprocess(self, command: List[str]):
        """Start the subprocess and stream its output."""
        self.log_widget.write(Text(f"$> {' '.join(command)}"))
        try:
            # Start the subprocess
            self._process_running = True
            self.subprocess = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Stream the subprocess output
            asyncio.create_task(self.stream_stdout(self.subprocess.stdout))
            asyncio.create_task(self.stream_stderr(self.subprocess.stderr))
            asyncio.create_task(self.extra_stdout_watcher())

            # Wait for the process to finish and display the final message once
            return_code = await self.subprocess.wait()

            if self._process_running:  # Only show this once
                self.log_widget.write(
                    Text(
                        f"[Command finished ({return_code})]\n",
                        style="red" if return_code else "green",
                    )
                )
                self._process_running = False

            self.subprocess = None
        except Exception as e:
            self.log_widget.write(Text(f"Error: {e}"))

    async def extra_stdout_watcher(self):
        SLEEP = 0.1

        while self.subprocess is not None:
            async with self.extra_stdout_lock:
                extra_before = self.extra_stdout

            await asyncio.sleep(SLEEP)

            async with self.extra_stdout_lock:
                extra_after = self.extra_stdout
                if extra_before and extra_before == extra_after:
                    self.log_widget.write(Text(self.extra_stdout.decode()))
                    self.extra_stdout = b""

    async def stream_stderr(self, stream):
        while not stream.at_eof():
            payload = await stream.readline()
            self.log_widget.write(Text(payload.decode(), style="red"))

    async def stream_stdout(self, stream):
        """Continuously read lines from the given stream and display them."""
        READSIZE = 2048

        while not stream.at_eof():
            payload = await stream.read(READSIZE)
            payload, *extra = payload.rsplit(b"\n", 1)

            async with self.extra_stdout_lock:
                payload = self.extra_stdout + payload
                self.log_widget.write(Text(payload.decode().strip()))

            if extra:
                async with self.extra_stdout_lock:
                    self.extra_stdout = extra[0]
            else:
                payload = b""
                async with self.extra_stdout_lock:
                    self.extra_stdout = b""

    async def send_input(self, user_input: str):
        """Send user input to the subprocess."""
        if self.subprocess and self.subprocess.stdin:
            self.subprocess.stdin.write(user_input.encode() + b"\n")
            await self.subprocess.stdin.drain()
            self.log_widget.write(f"\nU> {user_input}")

    async def action_terminate_subprocess(self):
        if self.subprocess:
            self.subprocess.terminate()
            await self.subprocess.wait()

    async def on_input_submitted(self, event: Input.Submitted):
        """Handle input submission."""
        user_input = self.user_input.value
        await self.send_input(user_input)
        self.user_input.value = ""

    def write(self, *args, **kwargs):
        self.log_widget.write(*args, **kwargs)

    def compose(self) -> ComposeResult:
        if self._process_running:
            yield self.user_input
            self.user_input.focus()
        yield self.log_widget

    async def on_unmount(self):
        await self.action_terminate_subprocess()
