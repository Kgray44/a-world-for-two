"""Collect one bounded actual metrics window during a master-owned game test.

Does not activate residents or alter the server. Separate before/after windows
are meaningful only with matched clients, camera, chunks and unrelated workload.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.artistic_review import request
from tools.playtest import guard


def collect(home,seconds,label,output):
    if not 30<=seconds<=120 or output.exists():raise ValueError('Fresh output and30..120second bounded window required')
    guard(0,1024**2)
    samples=[]
    for i in range(seconds//5+1):
        current=request(home,'metrics')
        samples.append({k:current.get(k)for k in ['at','tps','mspt','server_cpu','server_rss','loaded_chunks','entities','bridge_age_seconds','players_available']})
        samples[-1]['connected_player_count']=len(current.get('players')or{})
        print(f'{label}: sample{i+1}',flush=True)
        if i<seconds//5:time.sleep(5)
    values=[v['mspt']for v in samples if isinstance(v['mspt'],(int,float))and isinstance(v['bridge_age_seconds'],(int,float))and 0<=v['bridge_age_seconds']<=15]
    result={'format':'awft-tavern-actual-metrics-window:1','at':datetime.now(timezone.utc).isoformat(),
            'label':label,'samples':samples,'fresh_mspt_samples':len(values),
            'mspt_median':statistics.median(values)if values else None,
            'mspt_max':max(values)if values else None,
            'acceptance':False,'scope':'Actual metrics only; no synthetic inputs and no claim of causation or two-player acceptance'}
    raw=(json.dumps(result,indent=2)+'\n').encode()
    if len(raw)>128*1024:raise ValueError('Measurement output bound exceeded')
    guard(0,1024**2);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(raw)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--seconds',type=int,default=60);p.add_argument('--label',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.resolve().drive.upper()!='D:':raise ValueError('This bounded collector allocates only on D:')
    collect(a.home,a.seconds,a.label,a.output)
