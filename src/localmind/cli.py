import argparse
import uvicorn

from localmind.core.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="localmind")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    settings = Settings()
    host = args.host or settings.host
    port = args.port or settings.port
    uvicorn.run("localmind.api.app:create_app", factory=True, host=host, port=port)


if __name__ == "__main__":
    main()
