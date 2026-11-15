from __future__ import annotations

import concurrent.futures
from copy import deepcopy
import json
import re
import threading
import uuid

from .common import UserError, read_json, utcnow, write_json

HISTORY_BYTES = 4 * 1024 * 1024


def safe_message(value, limit=1000):
    text = str(value)
    text = re.sub(r'(?i)(authorization\s*[:=]\s*(?:bearer\s+)?|(?:access[_-]?token|password|secret|api[_-]?key)\s*[=:]\s*)[^\s,;]+', r'\1[redacted]', text)
    text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', text)
    return text.encode('utf-8')[:limit].decode('utf-8', errors='ignore')


def public_result(value):
    if isinstance(value, str):
        return safe_message(value)
    if isinstance(value, dict):
        return {key: '[redacted]' if re.search(r'(?i)password|secret|token|authorization|api.?key', str(key)) else public_result(item)
                for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [public_result(item) for item in value]
    return value


class Jobs:
    def __init__(self, path=None, storage=None, report_error=None):
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="awft-job")
        self._items = {}
        self._lock = threading.RLock()
        self._journal_lock = threading.Lock()
        self.path, self.storage = path, storage
        self.report_error = report_error
        self._closed = False
        if path is not None:
            if storage:
                storage.reserve(HISTORY_BYTES * 2)
            if path.exists() and path.stat().st_size > HISTORY_BYTES:
                raise UserError('Task history exceeds its bounded size. Preserve and inspect dashboard/jobs.json before restarting.')
            try:
                saved = read_json(path, [])
                if not isinstance(saved, list) or len(saved) > 50:
                    raise ValueError('Invalid task history')
                for item in saved:
                    if not isinstance(item, dict) or not re.fullmatch(r'[a-f0-9]{32}', item.get('id', '')):
                        raise ValueError('Invalid task record')
                    self._items[item['id']] = item
                    if item['status'] in ('queued', 'running'):
                        item.update(status='interrupted', finished=utcnow(), result=None,
                                    error='Control Room restarted before this task returned a result. Inspect server state and preserved files before retrying; the action was not replayed.')
                if saved:
                    self._persist()
            except (ValueError, KeyError, TypeError) as exc:
                raise UserError('Task history is damaged. Preserve and inspect dashboard/jobs.json before restarting.') from exc

    def _persist(self):
        # Only startup/workers write. Guard checks and fsync never hold the state
        # lock used by HTTP readers. Serialize journal snapshots to avoid an older
        # worker replacing a newer completed result.
        if self.path is None:
            return
        with self._journal_lock:
            if self.storage:
                self.storage.checkpoint(HISTORY_BYTES * 2)
            with self._lock:
                self._trim()
                while len(json.dumps(list(self._items.values()), indent=2, ensure_ascii=False).encode('utf-8')) > HISTORY_BYTES:
                    ident = next((ident for ident, item in self._items.items() if item['status'] not in ('queued', 'running')), None)
                    if ident is None:
                        raise UserError('Task history reached its bounded allocation')
                    del self._items[ident]
                snapshot = deepcopy(list(self._items.values()))
            write_json(self.path, snapshot)

    def _trim(self):
        for ident, item in list(self._items.items()):
            if len(self._items) <= 50:
                break
            if item['status'] not in ('queued', 'running'):
                del self._items[ident]

    def submit(self, title, function, *args):
        ident = uuid.uuid4().hex
        item = {"id": ident, "title": safe_message(title, 240), "status": "queued", "created": utcnow(),
                "messages": [], "result": None, "error": None}
        def notify(message):
            with self._lock:
                item["messages"] = (item["messages"] + [safe_message(message, 500)])[-40:]
            self._persist()
        def run():
            try:
                with self._lock:
                    item.update(status="running", started=utcnow())
                self._persist()
                result = function(*args, notify=notify)
                try:
                    result = public_result(result)
                    if len(json.dumps(result, indent=2, ensure_ascii=False).encode('utf-8')) > 32 * 1024:
                        result = {'note': 'Result exceeds the task-history limit. Inspect the operation files and console for details.'}
                except (ValueError, TypeError, RecursionError):
                    result = {'note': 'Task returned a result that cannot be displayed. Inspect the operation files and console for details.'}
                with self._lock:
                    item.update(status="complete", result=result, finished=utcnow())
            except Exception as exc:
                reference = self.report_error(exc) if self.report_error and not isinstance(exc, UserError) else None
                with self._lock:
                    message = safe_message(exc) if isinstance(exc, UserError) else f'The task failed ({type(exc).__name__}). Inspect server state and preserved files before retrying.' + (f' Error reference {reference} in logs/dashboard-errors.log.' if reference else '')
                    item.update(status="failed", error=message, finished=utcnow())
            finally:
                try:
                    self._persist()
                except (OSError, UserError):
                    with self._lock:
                        item['history_warning'] = 'Task history could not be saved. Inspect preserved files before retrying after a restart.'
        with self._lock:
            if self._closed:
                raise UserError('Control Room is closing; new tasks are disabled')
            if sum(x['status'] in ('queued', 'running') for x in self._items.values()) >= 4:
                raise UserError('Please wait for the current tasks to finish')
            self._items[ident] = item
            try:
                self.pool.submit(run)
            except Exception:
                self._items.pop(ident, None)
                raise
        return {"job": ident}

    def list(self):
        with self._lock:
            return deepcopy(list(self._items.values())[-50:][::-1])

    def close(self):
        with self._lock:
            self._closed = True
        self.pool.shutdown(wait=True)
