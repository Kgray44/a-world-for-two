"""Loopback read-only alias for the active private preview Control Room."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re
import sys
from urllib.parse import unquote, urlsplit


TARGET = 'http://127.0.0.1:8766'
MAX_TARGET = 8192


class PreviewRedirect(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *_args):
        pass  # Do not persist request paths, query values, tokens or unbounded logs.

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def reply(self, status, location=None):
        self.close_connection = True
        self.send_response_only(status)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', '0')
        self.send_header('Connection', 'close')
        if location is not None:
            self.send_header('Location', location)
        if status == 405:
            self.send_header('Allow', 'GET, HEAD')
        self.end_headers()

    def send_error(self, code, message=None, explain=None):
        self.reply(code)  # No reflected request text or HTML error body.

    def handle_expect_100(self):
        self.reply(405)
        return False

    def refuse_method(self):
        self.reply(405)

    def __getattr__(self, name):
        if name.startswith('do_'):
            return self.refuse_method
        raise AttributeError(name)

    def do_GET(self):
        port = self.server.server_address[1]
        if self.headers.get_all('Host', []) not in ([f'127.0.0.1:{port}'], [f'localhost:{port}']):
            self.reply(400)
            return
        # BaseHTTPRequestHandler normalizes leading //; inspect the original too.
        parts = self.requestline.split()
        target = parts[1] if len(parts) == 3 else ''
        try:
            decoded = unquote(target, errors='strict')
            parsed = urlsplit(target)
            valid = (0 < len(target) <= MAX_TARGET and target.isascii()
                     and target.startswith('/') and not target.startswith('//')
                     and not decoded.startswith('//') and '\\' not in decoded
                     and '#' not in target and not parsed.scheme and not parsed.netloc
                     and not re.search(r'%(?![a-fA-F0-9]{2})', target)
                     and all(32 < ord(ch) < 127 for ch in target)
                     and all(ord(ch) >= 32 and ord(ch) != 127 for ch in decoded))
        except (UnicodeError, ValueError):
            valid = False
        if not valid:
            self.reply(400)
            return
        self.reply(307, TARGET + target)

    do_HEAD = do_GET


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False
    request_queue_size = 8

    def __init__(self, address, handler):
        if address[0] != '127.0.0.1':
            raise ValueError('The preview alias is loopback-only')
        self.request_error_reported = False
        super().__init__(address, handler)

    def handle_error(self, request, client_address):
        if not self.request_error_reported:
            self.request_error_reported = True
            print('Preview alias request failed; no action was forwarded.', file=sys.stderr)


def make_server(port=8765):
    if type(port) is not int or not (port == 0 or 1024 <= port <= 65535) or port == 8766:
        raise ValueError('Use a separate unprivileged loopback listening port')
    return PreviewServer(('127.0.0.1', port), PreviewRedirect)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535 or args.port == 8766:
        parser.error('Use a separate unprivileged listening port, normally8765')
    try:
        server = make_server(args.port)
    except OSError:
        print('Preview alias could not bind; the existing service was left untouched.', file=sys.stderr)
        return 1
    print(f'Active PREVIEW alias: http://127.0.0.1:{args.port} -> {TARGET}; GET/HEAD only. Official world unchanged.', flush=True)
    try:
        server.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
