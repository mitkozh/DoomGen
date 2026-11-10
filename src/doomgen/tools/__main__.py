"""Command-line entry point for optional DoomGen tools."""

from __future__ import annotations

import argparse

from .acc import install_acc


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m doomgen.tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install", help="download an optional tool")
    install.add_argument("tool", choices=["acc"])
    install.add_argument(
        "--force",
        action="store_true",
        help="download again even if a cached copy exists",
    )

    args = parser.parse_args()

    if args.command == "install" and args.tool == "acc":
        path = install_acc(force=args.force)
        print(f"ACC installed at {path}")
        return 0

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
