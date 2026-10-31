#!/usr/bin/env python3
"""Serve the CartCheck practice fixture over HTTP on the loopback interface.

Usage:
    python fixtures/cartcheck/serve.py --port 8765

The server only binds 127.0.0.1, serves the fixture directory, and exits
cleanly on Ctrl+C.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import sys
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class FixtureRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Static file handler with cache disabled for repeatable tests."""

    def end_headers(self) -> None:  # noqa: D401 - http.server hook
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("[cartcheck] %s - %s\n" % (self.address_string(), fmt % args))
        sys.stderr.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="serve the CartCheck practice fixture")
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="TCP port (default: 8765)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0 <= args.port <= 65535:
        print(f"ERROR: invalid port {args.port} (expected 0-65535)", file=sys.stderr)
        return 2

    handler = functools.partial(FixtureRequestHandler, directory=str(FIXTURE_DIR))
    try:
        server = http.server.ThreadingHTTPServer((args.host, args.port), handler)
    except OSError as exc:
        print(f"ERROR: cannot bind {args.host}:{args.port}: {exc}", file=sys.stderr)
        return 2

    actual_host, actual_port = server.server_address[:2]
    print(f"CartCheck serving at http://{actual_host}:{actual_port}/", flush=True)
    print(f"Fixture directory: {FIXTURE_DIR}", flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nCartCheck server stopped.", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
