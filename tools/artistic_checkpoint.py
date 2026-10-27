"""Stopped, retained checkpoints of the private artistic world only."""
from pathlib import Path
import json
import time

from control_room.backups import Backups
from control_room.common import Layout, UserError, read_json, write_json, utcnow
from control_room.server import Server
from control_room.storage import Storage, tree_size
from .artistic_review import request
from .playtest import guard


class RetainedBackups(Backups):
    def prune(self):
        pass


def checkpoint(home, reason):
    layout = Layout(home)
    owner = read_json(layout.state/'artistic-owner.json', {})
    if (owner.get('format') != 'awft-artistic-stage:1'
            or Path(owner.get('home', '')).resolve() != layout.home
            or not layout.home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))):
        raise UserError('An owned, separate artistic staging world is required')
    guard(16*1024**2, 1024**3)
    size = sum(tree_size(root) for root in (layout.world, layout.server/'config', layout.server/'defaultconfigs'))
    if size > 768*1024**2:
        raise UserError('Checkpoint source exceeds the finite allocation')
    status = request(home, 'overview')['server']
    if status['state'] not in ('stopped', 'offline'):
        raise UserError('Stop the artistic server normally before this checkpoint')
    storage = Storage(layout)
    server = Server(layout, storage)
    if server.running():
        raise UserError('A staging writer still owns the world')
    result = RetainedBackups(layout, storage, server).create(reason=reason, resume=False)
    owner.update(backup=result['id'], backup_sha256=result['sha256'], updated=utcnow(),
                 status='stopped checkpoint retained; actual visual review in progress')
    write_json(layout.state/'artistic-owner.json', owner)
    write_json(layout.state/'settlement/backup-receipt.json', {
        'verified': True, 'id': result['id'], 'sha256': result['sha256'], 'at': utcnow(),
        'scope': 'Exact stopped private artistic checkpoint; no history pruned'})
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True, type=Path)
    parser.add_argument('--reason', required=True)
    args = parser.parse_args()
    checkpoint(args.home, args.reason)
