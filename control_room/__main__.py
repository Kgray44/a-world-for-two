from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from .common import UserError


def request_existing(port, home, action=None):
    base = "http://127.0.0.1:" + str(port)
    try:
        with urllib.request.urlopen(base + "/api/bootstrap", timeout=2) as response:
            info = json.loads(response.read(65536))
    except (OSError, ValueError):
        return False
    if info.get("app_id") != "awft-control-room" or Path(info.get("home", "")).resolve() != home.resolve():
        raise UserError("Port is already used by another Control Room data directory or service")
    if action:
        request = urllib.request.Request(base + "/api/" + action, data=b"{}",
            headers={"Content-Type": "application/json", "X-AWFT-CSRF": info["csrf"]}, method="POST")
        with urllib.request.urlopen(request, timeout=10) as response:
            print(response.read(65536).decode())
    return True


def main():
    parser = argparse.ArgumentParser(description="A World for Two: Control Room")
    parser.add_argument("action", nargs="?", default="run", choices=["run", "open", "start", "stop", "backup", "diagnose", "install", "repair"])
    parser.add_argument("--home", type=Path, default=Path(os.environ.get("AWFT_HOME", r"D:\A World for Two" if os.name == "nt" else "~/.local/share/a-world-for-two")).expanduser())
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--browser", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use an unprivileged port between 1024 and 65535")
    actions = {"start": "server/start", "stop": "server/stop", "backup": "backups/create",
               "diagnose": "health", "install": "setup/install", "repair": "setup/repair"}
    if request_existing(args.port, args.home, actions.get(args.action)):
        if args.browser or args.action == "open":
            webbrowser.open("http://127.0.0.1:" + str(args.port))
        return
    if args.action == "stop":
        raise UserError("Control Room is not running. Start it to recover the previous server's status; do not kill Java blindly.")
    from .web import Application, HTTPServer, make_handler
    app = Application(args.home)
    app.dashboard_port = args.port
    try:
        http = HTTPServer(("127.0.0.1", args.port), make_handler(app))
    except OSError:
        raise UserError("Cannot bind the local Control Room port. Another service may be using it.")
    app.start()
    if args.action in actions:
        result = app.post("/api/" + actions[args.action], {})
        print(json.dumps(result), flush=True)
    print("Control Room: http://127.0.0.1:" + str(args.port), flush=True)
    if args.browser or args.action == "open":
        webbrowser.open("http://127.0.0.1:" + str(args.port))
    try:
        if os.name != "nt":
            import signal
            signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        http.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()
        app.close()


if __name__ == "__main__":
    try:
        main()
    except UserError as exc:
        print("Control Room: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
