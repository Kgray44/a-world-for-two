"""Local, bounded administration of the existing native construction tools.

Receipts must be new, completed native operations. A queued console command alone
is never treated as proof that placement, a survey or a mechanism succeeded.
"""
from __future__ import annotations

import argparse
import json
import os
import hashlib
import time
import urllib.request
from pathlib import Path

from control_room.common import Layout, UserError, read_json


BASE = 'http://127.0.0.1:8765'


def native_read(path, default=None):
    """Allow the server's atomic rename while a Windows reader is open.

    Python's ordinary open omits FILE_SHARE_DELETE on Windows. Under paging an
    otherwise tiny polling read can overlap the native writer long enough to
    deny its rename. This changes sharing semantics, not verification results.
    """
    if os.name!='nt':return read_json(path,default)
    import ctypes
    import msvcrt
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    create=kernel.CreateFileW
    create.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE)
    create.restype=wintypes.HANDLE
    handle=create(str(path),0x80000000,7,None,3,0x08000000,None)
    if handle==ctypes.c_void_p(-1).value:
        error=ctypes.get_last_error()
        if error in (2,3):return default
        raise ctypes.WinError(error)
    try:
        descriptor=msvcrt.open_osfhandle(handle,os.O_RDONLY|os.O_BINARY)
    except BaseException:
        kernel.CloseHandle(wintypes.HANDLE(handle));raise
    with os.fdopen(descriptor,'r',encoding='utf-8') as stream:
        return json.load(stream)


def api(path, data=None):
    if data is None:
        with urllib.request.urlopen(BASE+'/api/'+path,timeout=10) as response:
            return json.load(response)
    info=api('bootstrap')
    if info.get('app_id')!='awft-control-room' or Path(info.get('home','')).resolve()!=Path(r'D:\A World for Two').resolve():
        raise UserError('The official local Control Room identity differs')
    request=urllib.request.Request(BASE+'/api/'+path,data=json.dumps(data).encode(),
        headers={'Content-Type':'application/json','Origin':BASE,'X-AWFT-CSRF':info['csrf']})
    with urllib.request.urlopen(request,timeout=15) as response:
        return json.load(response)


def require_clean_completion(result):
    """A finished native receipt cannot hide leaked temporary simulation tickets."""
    remaining=result.get('temporary_tickets_remaining',0)
    if type(remaining) is not int or remaining<0:
        raise UserError('Native ticket cleanup count is invalid; its exact receipt is preserved')
    if remaining or result.get('cleanup_required'):
        raise UserError('Native temporary-ticket cleanup is required; its exact receipt is preserved. Inspect engineering status and retry awftengine cancel before continuing')
    if result.get('error') or result.get('failures',0):
        raise UserError('Native operation failed; its exact receipt is preserved')


def native(command, *, receipt='status.json', archive=None, timeout=240):
    if not command.startswith(('awftbuild ','awftengine ')):
        raise UserError('This helper only invokes the bounded native construction tools')
    if not 1<=timeout<=300 or Path(receipt).name!=receipt:
        raise UserError('Receipt or timeout exceeds the local bound')
    folder=Layout(Path(r'D:\A World for Two')).state/'settlement'
    target=folder/receipt
    before=native_read(target,{})
    family='engineering' if receipt=='engineering-status.json' else 'settlement'
    markers_before=set(folder.glob(family+'-result-*.json.complete'))
    if api('overview').get('server',{}).get('state')!='online':
        raise UserError('The official server is not ready')
    api('console',{'command':command,'confirmed':True})
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        time.sleep(1)
        result=native_read(target,{})
        immutable=None
        for marker in set(folder.glob(family+'-result-*.json.complete'))-markers_before:
            final_path=marker.with_suffix('')
            if final_path.stat().st_size>8*1024**2:raise UserError('Native terminal receipt exceeds its bound')
            raw=final_path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=marker.read_text(encoding='utf-8').strip():
                raise UserError('Native terminal receipt hash differs')
            candidate=json.loads(raw)
            if command.split()[1] not in ('cancel','status') and candidate.get('operation')!=command.split()[1]:continue
            if len(command.split()[-1])==64 and candidate.get('plan_sha256')!=command.split()[-1]:continue
            result=candidate;immutable=final_path;break
        if result==before:continue
        if 'inspect ' in command:
            expected=list(map(int,command.split()[-3:]))
            if result.get('position')!=expected:continue
        elif not result.get('finished'):
            continue
        if archive:
            destination=folder/archive
            if destination.name!=archive or destination.exists():
                raise UserError('Choose a new immutable receipt name')
            destination.write_bytes((immutable or target).read_bytes())
        print(json.dumps({k:result[k] for k in ('status','operation','plan_sha256','failures','cycles','max_work_ms','error','temporary_tickets_remaining','cleanup_required','position','finished') if k in result}),flush=True)
        require_clean_completion(result)
        return result
    raise UserError('Native operation did not finish within the bound; inspect its journal before continuing')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command')
    parser.add_argument('--receipt',default='status.json')
    parser.add_argument('--archive')
    parser.add_argument('--timeout',type=int,default=240)
    args=parser.parse_args()
    native(args.command,receipt=args.receipt,archive=args.archive,timeout=args.timeout)
