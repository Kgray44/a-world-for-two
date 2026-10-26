"""Playit's installed Windows service, using its documented local JSON IPC.

Only status/state/subscription requests are sent. Account credentials remain in
Playit's own store. Start and stop use the official installed CLI, not process kills.
Protocol authority: playit-cloud/playit-agent, commit 633d650869a9cdb2c906efa9effc58aa8b7725a3.
"""
from __future__ import annotations

import collections
import contextlib
import ctypes
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

from .common import UserError, utcnow

PIPE = r'\\.\pipe\playitd-system'
MAX_LINE = 128 * 1024


def public_text(value, limit=600):
    text = str(value or '')[:4096]
    text = re.sub(r'(?i)(?:https?://)?(?:[a-z0-9.-]*\.)?playit\.gg/(?:claim|login|account/login)[^\s]*', '[account link hidden]', text)
    text = re.sub(r'(?i)\b(secret|token|password|authorization|key)\s*[:=]\s*[^\s,;]+', r'\1=[hidden]', text)
    text = re.sub(r'\b[a-fA-F0-9]{32,}\b', '[identifier hidden]', text)
    return re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', text)[:limit]


def safe_snapshot(status, lifecycle, stats):
    phase = lifecycle.get('state', status.get('phase', 'unknown'))
    agent = lifecycle.get('data', {}) if phase == 'running' else {}
    tunnels = []
    for row in agent.get('tunnels', [])[:32]:
        if not isinstance(row, dict):
            continue
        tunnels.append({key:public_text(row.get(key), 250) for key in ('display_address','destination','disabled_reason')} | {'is_disabled':row.get('is_disabled') is True})
    return {'state':public_text(phase,80),'pid':status.get('pid'), 'version':public_text(status.get('version'),60),
        'uptime_seconds':status.get('uptime_secs'), 'linked':status.get('has_secret') is True,
        'tunnels':tunnels, 'stats':{key:value for key in ('bytes_in','bytes_out','active_tcp','active_udp')
            if type(value:=stats.get(key)) is int and 0<=value<2**63},
        'notices':[public_text(n.get('message')) for n in agent.get('notices',[])[:10] if isinstance(n,dict)],
        'error':public_text((status.get('last_error') or {}).get('message')),
        'remote_join':'Unverified until a player connects from another network.'}


class Playit:
    def __init__(self):
        self.executable = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'playit_gg/bin/playit.exe'
        self._lock, self._actions, self._stop = threading.RLock(), threading.Lock(), threading.Event()
        self._thread = None
        self._status, self._lifecycle, self._stats = {}, {}, {}
        self._logs = collections.deque(maxlen=120)
        self._last, self._error = None, None

    def start_monitor(self):
        if os.name == 'nt' and not self._thread:
            self._thread = threading.Thread(target=self._monitor, name='awft-playit-ipc', daemon=True)
            self._thread.start()

    def close(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def snapshot(self):
        with self._lock:
            result = safe_snapshot(self._status,self._lifecycle,self._stats)
            service = None
            if os.name == 'nt':
                import psutil
                with contextlib.suppress(psutil.Error):
                    service = psutil.win_service_get('playitd').status()
            if service == 'stopped':
                result['state'] = 'stopped'
            result.update(installed=self.executable.is_file(),at=self._last,ipc_error=self._error,
                service_status=service, logs=list(self._logs),management='Existing Windows playitd service; dashboard closure leaves it running.')
            return result

    def _accept(self, envelope):
        if not isinstance(envelope,dict):
            raise ValueError('Invalid Playit envelope')
        kind, data = envelope.get('message_kind'), envelope.get('data',{})
        protocol = data.get('protocol',{}) if kind == 'hello' and isinstance(data,dict) else data
        if not isinstance(protocol,dict) or protocol.get('ipc_version') != 2:
            raise ValueError('Installed Playit IPC version is unsupported; update Playit from its official site')
        with self._lock:
            if kind == 'response':
                response = data.get('response',{})
                if response.get('type') == 'subscribe':
                    snap = response.get('data',{}).get('snapshot',{})
                    self._status,self._lifecycle,self._stats = (snap.get(k,{}) for k in ('status','lifecycle','stats'))
                elif response.get('type') == 'error':
                    raise ValueError(public_text(response.get('data',{}).get('message')))
            elif kind == 'event':
                event = data.get('event',{})
                name, value = event.get('type'), event.get('data',{})
                if name in ('status','lifecycle','stats') and isinstance(value,dict):
                    setattr(self,'_'+name,value)
                elif name == 'log' and isinstance(value,dict):
                    self._logs.append({'at':value.get('timestamp'),'level':public_text(value.get('level'),20),'message':public_text(value.get('message'))})
            self._last,self._error = utcnow(),None

    def _monitor(self):
        import msvcrt
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        peek = kernel.PeekNamedPipe
        peek.argtypes = [wintypes.HANDLE,wintypes.LPVOID,wintypes.DWORD,wintypes.LPDWORD,wintypes.LPDWORD,wintypes.LPDWORD]
        peek.restype = wintypes.BOOL
        while not self._stop.is_set():
            try:
                with open(PIPE,'r+b',buffering=0) as stream:
                    buffer, subscribed, last_data = b'',False,time.monotonic()
                    while not self._stop.is_set():
                        available=wintypes.DWORD()
                        if not peek(msvcrt.get_osfhandle(stream.fileno()),None,0,None,ctypes.byref(available),None):
                            raise OSError('Playit local service disconnected')
                        if available.value:
                            buffer += stream.read(min(available.value,MAX_LINE+1-len(buffer)))
                            if len(buffer)>MAX_LINE:raise ValueError('Playit IPC exceeded its message limit')
                            last_data=time.monotonic()
                            while b'\n' in buffer:
                                line,buffer=buffer.split(b'\n',1)
                                envelope=json.loads(line)
                                self._accept(envelope)
                                if envelope.get('message_kind')=='hello' and not subscribed:
                                    stream.write(b'{"ipc_version":2,"request_id":1,"request":{"type":"subscribe"}}\n')
                                    subscribed=True
                        elif time.monotonic()-last_data>30:
                            raise OSError('No fresh Playit IPC update in 30 seconds')
                        self._stop.wait(.15)
            except (OSError,ValueError,TypeError,KeyError) as error:
                with self._lock:
                    self._error=public_text(error)
                    self._status,self._lifecycle,self._stats={},{},{}
                self._stop.wait(3)

    def action(self, action, confirmed=False, notify=lambda _:None):
        if action not in ('start','stop') or confirmed is not True:
            raise UserError('Choose and confirm a Playit service action')
        if os.name!='nt' or not self.executable.is_file():
            raise UserError('Install the official Playit Windows application first')
        with self._actions:
            # Fixed CLI verbs; no browser-supplied arguments, paths or credentials.
            try:
                result=subprocess.run([str(self.executable),action],capture_output=True,text=True,
                    timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
            except subprocess.TimeoutExpired as error:
                raise UserError('Playit did not confirm the service action within 20 seconds; inspect its status before retrying') from error
            if result.returncode:
                raise UserError('Playit service action failed: '+public_text(result.stderr or result.stdout))
            with self._lock:
                self._logs.append({'at':utcnow(),'level':'info','message':action.title()+' requested through the official Playit CLI.'})
            notify('Playit service '+action+' requested; live IPC status will confirm its connection.')
            return {'requested':action,'status':self.snapshot()}
