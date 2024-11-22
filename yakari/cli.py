import argparse
import subprocess

from .app import YakariApp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command_name", help="Name of the command to execute")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If toggled, Yakari only prints the command rather than running it.",
    )
    args = parser.parse_args()

    app = YakariApp(args.command_name)
    cmd = app.run()

    if cmd:
        if args.dry_run:
            print(cmd)
        else:
            subprocess.run(cmd)


if __name__ == "__main__":
    main()
