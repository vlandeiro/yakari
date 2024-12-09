import argparse
import subprocess

from .app import YakariApp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command_name", help="Name of the command to execute")
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="If toggled, Yakari only prints the command rather than running it.",
    )
    parser.add_argument(
        "-n",
        "--native",
        action="store_true",
        help="When toggled, run the command in the original shell instead of within the Yakari menu.",
    )
    args = parser.parse_args()

    app = YakariApp(args.command_name, args.dry_run, not args.native)
    command = app.run()
    if command:
        subprocess.run(command)


if __name__ == "__main__":
    main()
