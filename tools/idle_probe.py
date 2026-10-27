"""A fixed, bounded ticket experiment on an explicitly owned disposable server.

Serves the normal Control Room afterward. Never sends arbitrary browser commands.
No probe runs while a player is online; the exact nine temporary tickets are removed
on completion or interruption. This is deliberately distinct from clean idle.
"""
from __future__ import annotations

import argparse
import copy
import threading
import time
from pathlib import Path

from control_room.client_metrics import ClientMetrics
from control_room.common import Layout, REPO, UserError, digest, read_json, utcnow, write_json
from control_room.metrics import DIAGNOSTIC_SECONDS, measurement_freshness
from control_room.web import Application, HTTPServer, make_handler
from .live_samples import fresh_players, fresh_tick
from .playtest_update import owned_pair


def require_idle(sample, now=None):
    if not fresh_players(sample, now):
        raise UserError('Player presence unavailable; no idle or force-load decision is permitted')
    if sample['players']:
        raise UserError('Player joined; ticket experiment interrupted and temporary tickets removed')


def admit_probe(sample, now=None):
    require_idle(sample, now)
    now = time.time() if now is None else now
    diagnostic = sample.get('chunk_diagnostics') or {}
    dimensions = diagnostic.get('dimensions')
    if (diagnostic.get('unavailable') or not isinstance(dimensions, dict) or not dimensions
            or not measurement_freshness(diagnostic.get('at'), now, DIAGNOSTIC_SECONDS)['current']
            or any(not isinstance(row, dict) or type(row.get('vanilla_forced_chunks')) is not int
                   or row['vanilla_forced_chunks'] < 0 for row in dimensions.values())):
        raise UserError('Forced-chunk baseline unavailable; controlled probe not run')
    if any(row['vanilla_forced_chunks'] for row in dimensions.values()):
        raise UserError('Existing forced chunks are preserved; controlled probe not run')


def experiment(app):
    result = {'at':utcnow(),'pack_sha256':digest(REPO/'packwiz/pack.toml'),'status':'pending','phases':[]}
    target=app.layout.logs/('idle-ticket-probe-'+str(time.time_ns())+'.json')
    forced=False
    def checked(sample, probe=False):
        try:
            (admit_probe if probe else require_idle)(sample)
        except UserError as error:
            result['interrupted_observation'] = {'at': utcnow(), 'reason': str(error), 'sample': copy.deepcopy(sample)}
            raise
    def phase(name,seconds):
        end=time.monotonic()+seconds
        print('Idle probe: '+name,flush=True)
        while time.monotonic()<end:
            sample=app.metrics.latest()
            if not app.server.running():raise UserError('Server exited during the idle probe')
            checked(sample)
            time.sleep(1)
        sample=copy.deepcopy(app.metrics.latest())
        checked(sample)
        if not fresh_tick(sample.get('tick_at')):raise UserError('Native telemetry is stale')
        result['phases'].append({'at':utcnow(),'phase':name,'sample':sample})
        write_json(target,result)
    try:
        app.start_world(notify=print)
        phase('startup without player or probe tickets',90)
        sample=app.metrics.latest()
        checked(sample, probe=True)
        forced=True
        app.server._write('forceload add 2048 2048 2080 2080')
        phase('controlled nine-chunk force-load region',60)
        app.server._write('forceload remove 2048 2048 2080 2080')
        forced=False
        phase('five minutes after controlled force-load removal',300)
        result['status']='completed; compare ticket sources and completed/ticking chunks, not holder count alone'
    except BaseException as error:
        result.update(status='incomplete; exact failure preserved',error=str(error))
        print('Idle probe: '+str(error),flush=True)
    finally:
        if forced and app.server.running():
            app.server._write('forceload remove 2048 2048 2080 2080')
        result['finished']=utcnow()
        write_json(target,result)
        print('Idle probe receipt: '+str(target),flush=True)


def run(parent,ident,serve_only=False):
    layout,_,_,_=owned_pair(Layout(parent),ident)
    app=Application(layout.home)
    app.metrics.clients=ClientMetrics(Layout(parent))
    http=HTTPServer(('127.0.0.1',8766),make_handler(app))
    try:
        app.start()
        if serve_only:
            print('Start job: '+str(app.post('/api/server/start', {})),flush=True)
        else:
            threading.Thread(target=experiment,args=(app,),daemon=True).start()
        print('Updated candidate dashboard: http://127.0.0.1:8766/',flush=True)
        http.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()
        app.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--id',required=True)
    parser.add_argument('--serve-only',action='store_true',help='Start the owned pair normally without repeating the completed ticket experiment')
    args=parser.parse_args()
    run(args.home,args.id,args.serve_only)
