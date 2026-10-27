"""Sequential native placement/verification of independently prepared districts.

All design work can run in parallel; this deliberately serializes the one real
world writer. A failed native check stops the queue and preserves its receipt.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from control_room.common import Layout, UserError, digest, read_json, write_json, utcnow
from tools.settlement_live import native


def deploy(source, label):
    layout=Layout(Path(r'D:\A World for Two'));folder=layout.state/'settlement'
    source=Path(source).resolve()
    if source.parent!=folder.resolve() or not source.is_file() or source.is_symlink():
        raise UserError('Choose one prepared native plan in the owned settlement folder')
    if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
        raise UserError('Use one simple unique receipt label')
    plan=read_json(source)
    backup=read_json(folder/'backup-receipt.json')
    if not backup.get('verified') or plan.get('backup_sha256')!=backup['sha256']:
        raise UserError('Plan does not bind to the current verified backup')
    sha=digest(source)
    receipt_name=label+'-'+sha[:12]
    previous=read_json(folder/(receipt_name+'-verify.json'),{})
    if previous.get('plan_sha256')==sha and previous.get('finished') and not previous.get('failures') and previous.get('operation')=='verify':
        print(label+': prior exact native verification retained; no repeated placement',flush=True)
        return
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
        r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1',
        '-EstimatedCBytes','0','-EstimatedDBytes',str(512*1024**2)],check=True,timeout=30)
    if not read_json(folder/'status.json',{}).get('finished'):
        raise UserError('Another native construction operation is still active')
    shutil.copy2(source,folder/'plan.json')
    if digest(folder/'plan.json')!=sha:raise UserError('Native plan staging changed bytes')
    native('awftbuild place '+sha,archive=receipt_name+'-place.json')
    native('awftbuild verify '+sha,archive=receipt_name+'-verify.json')
    native('awftbuild map '+sha,archive=receipt_name+'-map.json')
    write_json(folder/(receipt_name+'-deployment.json'),{'at':utcnow(),'plan':source.name,'sha256':sha,
        'label':label,'placement':'native complete','block_verification':'native pass',
        'map':'native dirty-chunk notifications queued; browser tiles still require review',
        'visual_review':'pending','functionality':'separate from placement verification'})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('plan',type=Path);parser.add_argument('--label',required=True)
    args=parser.parse_args();deploy(args.plan,args.label)
