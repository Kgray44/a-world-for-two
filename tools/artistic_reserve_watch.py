"""Bounded reserve journal for one explicitly owned private JVM; no time limit."""
from pathlib import Path
import argparse
import json
import subprocess
import time

import psutil

from tools.artistic_review import request


def watch(home, pid, born, journal):
    home, journal = Path(home).resolve(), Path(journal).resolve()
    if (home.parent != Path(r'D:\A World for Two\staging\world-tests')
            or journal.parent != home/'logs' or journal.exists()):
        raise ValueError('New bounded journal in the owned private stage required')
    owner = psutil.Process(pid)
    if (owner.create_time() != born or owner.name().lower() != 'java.exe'
            or Path(owner.cwd()).resolve() != home/'server'):
        raise ValueError('Exact owned Minecraft process identity required')
    journal.touch(exist_ok=False)
    while True:
        try:
            if not owner.is_running() or owner.create_time() != born:
                return
        except psutil.NoSuchProcess:
            return
        result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1',
            '-EstimatedCBytes', '17179869184', '-EstimatedDBytes', '8589934592'],
            capture_output=True, text=True, timeout=35, creationflags=subprocess.CREATE_NO_WINDOW)
        row = json.loads(result.stdout.strip().splitlines()[-1])
        row.update(owned_server_pid=pid, timed_shutdown=False,
                   coverage='Owned private writer monitoring; not an OS quota or external application control')
        raw = (json.dumps(row)+'\n').encode()
        if journal.stat().st_size+len(raw) <= 65536:
            with journal.open('ab') as out:
                out.write(raw)
        if result.returncode or not row.get('allowed'):
            if request(home, 'overview')['server'].get('pid') == pid:
                request(home, 'server/stop', {})
            return
        time.sleep(240)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True, type=Path)
    parser.add_argument('--pid', required=True, type=int)
    parser.add_argument('--born', required=True, type=float)
    parser.add_argument('--journal', required=True, type=Path)
    args = parser.parse_args()
    watch(args.home, args.pid, args.born, args.journal)
