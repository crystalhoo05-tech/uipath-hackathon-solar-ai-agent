"""Application entry point."""

import argparse
import sys

from dotenv import load_dotenv

from hackathon_ai_uipath import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hackathon-ai-uipath",
        description="Solar post-installation diagnostic agent API",
    )
    parser.add_argument("--host", default=None, help="Host to bind (default: from env)")
    parser.add_argument("--port", type=int, default=None, help="Port (default: from env)")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.host or args.port:
        from hackathon_ai_uipath.config import get_settings

        settings = get_settings()
        if args.host:
            settings.host = args.host
        if args.port:
            settings.port = args.port

    from hackathon_ai_uipath.api.app import run

    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
