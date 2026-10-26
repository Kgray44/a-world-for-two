from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import urllib.parse
import urllib.request
from pathlib import Path

from .common import UserError

UA = "Kgray44/a-world-for-two/0.1 (github.com/Kgray44/a-world-for-two)"
ALLOWED_DOWNLOAD_HOSTS = {"cdn.modrinth.com", "maven.neoforged.net", "github.com",
                          "objects.githubusercontent.com", "release-assets.githubusercontent.com",
                          "raw.githubusercontent.com", "meta.prismlauncher.org",
                          "ldtteam.jfrog.io"}


def public_https(url, allowed=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise UserError("Only public HTTPS project URLs are supported")
    if allowed is not None and parsed.hostname not in allowed:
        raise UserError("Download host is not an approved upstream")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise UserError("Private-network URLs are not allowed")
    except socket.gaierror as exc:
        raise UserError("Upstream name could not be resolved") from exc
    return url


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        origin, target = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        # The author's Maven serves its immutable artifacts from this exact GCS
        # filestore. Permit that verified redirect, never arbitrary GCS downloads.
        author_filestore = (origin.hostname == 'ldtteam.jfrog.io'
            and origin.path.startswith('/artifactory/mods-maven/com/ldtteam/')
            and target.hostname == 'storage.googleapis.com'
            and target.path.startswith('/art-ldtteam-filestore-1532847948/filestore/'))
        public_https(newurl, ALLOWED_DOWNLOAD_HOSTS | {'storage.googleapis.com'} if author_filestore else ALLOWED_DOWNLOAD_HOSTS)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def api(path, params=None):
    if not path.startswith("/") or ".." in path:
        raise UserError("Invalid Modrinth API path")
    url = "https://api.modrinth.com/v2" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise UserError("Upstream metadata exceeded the safety limit")
    return json.loads(raw)


def download(url: str, path: Path, expected_size: int, expected_hash: str,
             algorithm: str, storage, notify=lambda _: None):
    if not 0 < expected_size <= 256 * 1024 * 1024:
        raise UserError("Downloads must have a known size of at most 256 MiB")
    if algorithm not in ("sha256", "sha512", "sha1") or not expected_hash:
        raise UserError("An upstream integrity hash is required")
    public_https(url, ALLOWED_DOWNLOAD_HOSTS)
    storage.reserve(expected_size, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    if partial.exists():
        raise UserError("A prior partial download is preserved; inspect it before retrying")
    hasher = hashlib.new(algorithm)
    received = 0
    try:
        opener = urllib.request.build_opener(SafeRedirect())
        with opener.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as response, partial.open("xb") as stream:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                received += len(block)
                if received > expected_size:
                    raise UserError("Download exceeded its declared allocation")
                stream.write(block)
                hasher.update(block)
                storage.checkpoint(expected_size - received, path)
        if received != expected_size or hasher.hexdigest() != expected_hash.lower():
            raise UserError("Downloaded file failed its size or integrity check; partial preserved")
        os.replace(partial, path)
        notify("Verified " + path.name)
    except Exception:
        # Failed receipts and bytes stay available for diagnosis, never silently reused.
        raise
    return path
