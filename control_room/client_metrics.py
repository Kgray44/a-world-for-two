"""Read small local measurements only from verified, owned Prism instances."""
from __future__ import annotations

import math
import time
from datetime import datetime
from pathlib import Path

import psutil

from .common import GiB, UserError, contained, read_json


class ClientMetrics:
    def __init__(self, layout):
        self.layout = layout
        self.processes = {}

    def collect(self):
        rows, alive = [], set()
        folder = self.layout.home / 'instances'
        if not folder.is_dir():
            return rows
        for instance in folder.iterdir():
            if not instance.is_dir() or instance.is_symlink() or instance.is_junction():
                continue
            try:
                path = contained(instance, '.minecraft/awft-client-metrics.json')
                owner_path = instance / 'awft-owned.json'
                if not path.is_file() or path.stat().st_size > 65536 or not owner_path.is_file() or owner_path.stat().st_size > 512*1024:
                    continue
                owner = read_json(instance / 'awft-owned.json', {})
                if owner.get('format') != 'awft-owned-client:1' or Path(owner.get('root', '')).resolve() != instance.resolve():
                    continue
                data = read_json(path)
                stamp = datetime.fromisoformat(data['at'].replace('Z', '+00:00')).timestamp()
                if data.get('format') != 'awft-client-metrics:1' or not -2 <= time.time() - stamp <= 15 or type(data.get('pid')) is not int:
                    continue
                process = psutil.Process(data['pid'])
                started = datetime.fromisoformat(data['process_started'].replace('Z', '+00:00')).timestamp()
                if abs(process.create_time() - started) > 2 or process.name().lower() not in ('java.exe', 'javaw.exe', 'java') or Path(process.cwd()).resolve() != path.parent.resolve():
                    continue
                row = {'instance':instance.name, 'player':owner.get('player'), 'pid':process.pid, 'at':data['at'],
                       'rss':process.memory_info().rss, 'cpu_percent_host':None,
                       'focused':data.get('focused') is True, 'in_world':data.get('in_world') is True,
                       'screen':str(data.get('screen', 'unknown'))[:100], 'camera':str(data.get('camera', 'unknown'))[:40]}
                for key, maximum in [('fps',100000), ('heap_used',64*GiB), ('heap_max',64*GiB)]:
                    value=data.get(key)
                    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= maximum:
                        raise ValueError('Invalid client measurement')
                    row[key] = value
                frame = data.get('frame_interval_ms')
                if frame:
                    if type(frame.get('samples')) is not int or not 1 <= frame['samples'] <= 4096:
                        raise ValueError('Invalid frame sample count')
                    if any(type(frame.get(k)) not in (int,float) or not math.isfinite(frame[k]) or not 0 <= frame[k] <= 3_600_000 for k in ('mean','p50','p95','max')):
                        raise ValueError('Invalid frame intervals')
                    row['frame_interval_ms'] = {k:frame[k] for k in ('samples','mean','p50','p95','max')}
                if data.get('integration_error'):
                    row['integration_error'] = str(data['integration_error'])[:300]
                prior = self.processes.get(process.pid)
                if prior and abs(prior.create_time()-started) <= 2:
                    row['cpu_percent_host'] = prior.cpu_percent()/(psutil.cpu_count() or 1)
                else:
                    process.cpu_percent()
                    self.processes[process.pid] = process
                alive.add(process.pid)
                rows.append(row)
                if len(rows) >= 8:
                    break
            except (OSError, ValueError, KeyError, TypeError, UserError, psutil.Error):
                continue
        self.processes = {pid:p for pid,p in self.processes.items() if pid in alive}
        return rows
