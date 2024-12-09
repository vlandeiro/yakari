import argparse
import sys

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
        help="When toggled, run the command in the original shell instead of within the Yakari menu."
    )
    args = parser.parse_args()

    app = YakariApp(args.command_name, args.dry_run, not args.native)
    result = app.run()

    if result is not None:
        print(result.stderr, file=sys.stderr)
        print(result.stdout, file=sys.stdout)


if __name__ == "__main__":
    main()
