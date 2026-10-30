"""Bounded transport-window sampling of existing native bridge telemetry.

No server/client, HTTP/native command, chunk or gameplay operation is started.
The master must coordinate each declared phase; collection cannot prove what the
players were doing or exclude concurrent construction by itself.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time

import psutil

from control_room.common import UserError, digest, utcnow
from tools.artistic_quay_prototype import bounded, context, write_bundle
from tools.playtest import guard

MIB=1024**2
PHASES=('baseline','active-transport','stopped-idle')


def timestamp(value):
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        if result.tzinfo is None:raise ValueError('missing timezone')
        return result.timestamp()
    except (ValueError,TypeError,AttributeError)as error:
        raise UserError('An actual native timestamp is required')from error


def sample_row(raw, *, now, pid, started):
    if not isinstance(raw,bytes)or not 0<len(raw)<=2*MIB:
        raise UserError('Finite actual native metrics required')
    value=json.loads(raw)
    if value.get('format')!='awft-metrics:1' or value.get('pid')!=pid or value.get('process_started')!=started:
        raise UserError('Native telemetry belongs to another server process')
    age=now-timestamp(value.get('at'))
    if not -.25<=age<=15:
        raise UserError('Stale/future telemetry cannot supply a transport sample')
    for key in ('tps','mspt','interval_ms'):
        number=value.get(key)
        if type(number)not in(int,float)or not math.isfinite(number)or number<0:
            raise UserError('Real finite native timing measurements required')
    ticks=value.get('ticks_sampled');interval=value['interval_ms']
    if type(ticks)is not int or not 1<=ticks<=100000 or not 1<=interval<=120000:
        raise UserError('Actual bounded positive tick interval required')
    expected=ticks*1000/interval
    if abs(value['tps']-expected)>max(.01,expected*.01):
        raise UserError('TPS/tick-count/interval arithmetic disagrees')
    if not isinstance(value.get('players'),dict):
        raise UserError('Actual native roster unavailable')
    return {'at':value['at'],'pid':pid,'process_started':started,'tps':value['tps'],
            'mspt':value['mspt'],'ticks_sampled':ticks,'interval_ms':interval,
            'loaded_chunks':value.get('loaded_chunks'),'entities':value.get('entities'),
            'heap_used':value.get('heap_used'),'gc_collections':value.get('gc_collections'),
            'gc_collection_ms':value.get('gc_collection_ms'),'player_uuids':sorted(value['players']),
            'source_file_sha256':hashlib.sha256(raw).hexdigest(),'observed_age_seconds':age}


def summarize(rows):
    if not rows:raise UserError('No fresh native timing intervals were collected')
    keys={(row['pid'],row['process_started'])for row in rows}
    if len(keys)!=1 or len({row['at']for row in rows})!=len(rows):
        raise UserError('Process changes and duplicate intervals cannot form one profile')
    ordered=sorted(rows,key=lambda row:timestamp(row['at']))
    for previous,current in zip(ordered,ordered[1:]):
        elapsed=timestamp(current['at'])-timestamp(previous['at'])
        if elapsed+.1<current['interval_ms']/1000:
            raise UserError('Overlapping native sample intervals cannot be double counted')
    ticks=sum(row['ticks_sampled']for row in rows)
    wall_ms=sum(row['interval_ms']for row in rows)
    return {'intervals':len(rows),'ticks_sampled':ticks,'measured_interval_seconds':wall_ms/1000,
            'aggregate_tps':ticks*1000/wall_ms,
            'tick_weighted_mean_mspt':sum(row['mspt']*row['ticks_sampled']for row in rows)/ticks,
            'worst_interval_mean_mspt':max(row['mspt']for row in rows),
            'first_native_at':ordered[0]['at'],'last_native_at':ordered[-1]['at'],
            'player_rosters_stable':len({tuple(row['player_uuids'])for row in rows})==1,
            'limits':'MSPT values are native interval means, not per-tick percentiles. Declared phase and external-load control need master corroboration.'}


def collect(home, output, phase, seconds=60):
    if phase not in PHASES or type(seconds)is not int or not 30<=seconds<=120:
        raise UserError('Choose one declared transport phase and30..120seconds')
    reserve=guard(0,16*MIB)
    home,output,current,_=context(home,output)
    source=home/'dashboard/server-metrics.json';first=bounded(source,2*MIB)
    pid,started=first.get('pid'),first.get('process_started')
    if type(pid)is not int or pid<1:
        raise UserError('Actual native server PID required')
    process=psutil.Process(pid)
    if abs(process.create_time()-timestamp(started))>.1 or Path(process.cwd()).resolve()!=home/'server':
        raise UserError('Actual process start/CWD differs from the owned server')
    identity={'pid':pid,'started':started,'os_create_time':process.create_time()}
    active=bounded(home/'packwiz/active.json')
    rows,errors,seen=[],[],set();begin=time.monotonic();window_started=time.time();failure=None
    while time.monotonic()-begin<seconds:
        if not process.is_running() or abs(process.create_time()-identity['os_create_time'])>.1:
            failure='Owned process ended or changed during observation';break
        try:
            if not source.is_file() or not 0<source.stat().st_size<=2*MIB:
                raise UserError('Native telemetry file missing or unbounded')
            with source.open('rb')as stream:
                raw=stream.read(2*MIB+1)
            row=sample_row(raw,now=time.time(),pid=pid,started=started)
            if row['at']not in seen:
                # Exclude the interval that began before the declared window.
                if timestamp(row['at'])-row['interval_ms']/1000>=window_started:
                    rows.append(row)
                seen.add(row['at'])
        except (UserError,OSError,ValueError)as error:
            errors.append({'observed_at':utcnow(),'error':str(error)[:512]})
        if len(rows)>128 or len(errors)>128:
            failure='Finite profile rows/error bound reached';break
        time.sleep(.5)
    try:
        summary=summarize(rows)if rows else None
    except UserError as error:
        summary=None;failure=str(error)
    complete=failure is None and not errors and summary is not None and summary['measured_interval_seconds']>=seconds*.75
    try:
        if bounded(home/'packwiz/active.json')!=active:
            failure='Installed manifest changed during profile';complete=False
    except (UserError,OSError,ValueError)as error:
        failure='Installed manifest unavailable at profile end: '+str(error)[:512];complete=False
    manifest={'format':'awft-transport-native-profile:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
              'phase_declared_by_operator':phase,'requested_seconds':seconds,'window_started':datetime.fromtimestamp(window_started,timezone.utc).isoformat(),'actual_elapsed_seconds':time.monotonic()-begin,
              'identity':identity,'active_pack':active,'source_checkpoint_sha256':current['sha256'],
              'timing_collection_complete':complete,'failure':failure,'read_errors':errors,'summary':summary,
              'native_actions':0,'world_writes':0,'new_Minecraft_processes':0,'storage_guard':reserve,
              'acceptance':'Measured timing only; no ride, attribution, multiplayer, restart or owner acceptance is inferred.'}
    return write_bundle(output,{'native-timing-intervals.json':rows},manifest)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--phase',choices=PHASES,required=True);parser.add_argument('--seconds',type=int,default=60)
    args=parser.parse_args()
    print(json.dumps(collect(args.home,args.output,args.phase,args.seconds),indent=2))
