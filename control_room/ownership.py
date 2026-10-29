"""Linux process leases; inherited by Java so supervisor death cannot admit a twin."""
from __future__ import annotations

import os
from pathlib import Path

from .common import UserError


class ProcessLease:
    def __init__(self, path: Path):
        import fcntl
        flags = os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW
        self.fd = os.open(path, flags, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(self.fd)
            self.fd = None
            raise UserError("Another process owns this runtime; no second writer was started") from exc

    def close(self):
        # Do not LOCK_UN: an inherited Java descriptor must retain the lease.
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
