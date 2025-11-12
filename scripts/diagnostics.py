import argparse
import asyncio
from pathlib import Path

from localmind.core.settings import Settings
from localmind.indexing.snapshot import export_repository_snapshot, print_diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description="LocalMind diagnostics and snapshot tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    diag = subparsers.add_parser("diagnostics", help="Print global indexing diagnostics")
    diag.add_argument("--data-dir", default=None)

    export = subparsers.add_parser("export", help="Export repository index snapshot")
    export.add_argument("repository_id", type=int)
    export.add_argument("--output", required=True)
    export.add_argument("--data-dir", default=None)

    args = parser.parse_args()
    settings = Settings()
    if args.data_dir:
        settings.data_dir = Path(args.data_dir)

    if args.command == "diagnostics":
        asyncio.run(print_diagnostics(settings))
        return

    if args.command == "export":
        output = asyncio.run(
            export_repository_snapshot(settings, args.repository_id, Path(args.output))
        )
        print(str(output))


if __name__ == "__main__":
    main()
