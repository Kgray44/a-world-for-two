from __future__ import annotations

import concurrent.futures
import threading
import traceback
import uuid

from .common import UserError, utcnow


class Jobs:
    def __init__(self):
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="awft-job")
        self._items = {}
        self._lock = threading.RLock()

    def submit(self, title, function, *args):
        with self._lock:
            if sum(x["status"] in ("queued", "running") for x in self._items.values()) >= 4:
                raise UserError("Please wait for the current tasks to finish")
            ident = uuid.uuid4().hex
            item = {"id": ident, "title": title, "status": "queued", "created": utcnow(),
                    "messages": [], "result": None, "error": None}
            self._items[ident] = item
        def notify(message):
            with self._lock:
                item["messages"] = (item["messages"] + [str(message)[:1000]])[-100:]
        def run():
            with self._lock:
                item.update(status="running", started=utcnow())
            try:
                result = function(*args, notify=notify)
                with self._lock:
                    item.update(status="complete", result=result, finished=utcnow())
            except Exception as exc:
                with self._lock:
                    item.update(status="failed", error=str(exc), finished=utcnow())
        self.pool.submit(run)
        return {"job": ident}

    def list(self):
        with self._lock:
            return [dict(x, messages=list(x["messages"])) for x in list(self._items.values())[-50:]][::-1]

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=True)
