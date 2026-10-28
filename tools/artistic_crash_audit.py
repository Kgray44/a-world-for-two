"""Read-only geometry audit of an explicitly UNCLEAN retained crash archive.

This does not turn a crash preservation into a clean checkpoint, update owner
bindings, operate Minecraft, or authorize replay of missing inventories.
"""
from pathlib import Path
import zipfile

from control_room.common import UserError, digest, read_json
from tools.settlement_attractions import BackupWorld


class CrashWorld(BackupWorld):
    def __init__(self, receipt_path):
        receipt_path = Path(receipt_path).resolve()
        base = Path(r'D:\A World for Two\staging\world-tests').resolve()
        if not receipt_path.is_relative_to(base) or receipt_path.is_symlink():
            raise UserError('An owned private unclean preservation is required')
        receipt = read_json(receipt_path)
        archive = Path(receipt.get('archive', '')).resolve()
        if (receipt.get('format') != 'awft-unclean-crash-preservation:1'
                or receipt.get('server_running') is not False
                or archive.parent != receipt_path.parent
                or archive.stat().st_size > 768*1024**2
                or digest(archive) != receipt.get('archive_sha256')):
            raise UserError('The bounded retained crash archive differs')
        rows = receipt.get('files', [])
        if not rows or len(rows) > 4096 or len({r['path'] for r in rows}) != len(rows):
            raise UserError('Finite unique crash archive inventory required')
        self.archive = zipfile.ZipFile(archive)
        self.files = {r['path']: {'size': r['bytes'], 'sha256': r['sha256']} for r in rows}
        if self.archive.namelist() != [r['path'] for r in rows]:
            self.archive.close()
            raise UserError('Crash archive inventory differs')
        self.prefix = 'region/'
        self.regions, self.chunks, self.sources, self.protected = {}, {}, [], set()


ORIENTATION = frozenset(('facing', 'axis', 'half', 'type', 'part', 'hinge', 'multiblock'))


def parts(text):
    name, sep, tail = text.partition('[')
    return name, dict(p.split('=', 1) for p in tail[:-1].split(',')) if sep else {}


def audit(snapshot, plan):
    """Match native construction identity/orientation; retain all discrepancies."""
    palette = plan['palette']
    differences = []
    unavailable = {}
    for x, y, z, index in plan['blocks']:
        wanted = palette[index]
        chunk = (x//16, z//16)
        if chunk in unavailable:
            unavailable[chunk]['cells'] += 1
            continue
        try:
            actual = snapshot.state((x, y, z))
        except UserError as error:
            unavailable[chunk] = {'chunk': list(chunk), 'cells': 1, 'error': str(error)}
            continue
        wn, wp = parts(wanted); an, ap = parts(actual)
        if wn != an or any(ap.get(k) != v for k, v in wp.items() if k in ORIENTATION):
            differences.append({'pos': [x, y, z], 'wanted': wanted, 'actual_unclean_saved': actual})
    return {'cells': len(plan['blocks']), 'differences': differences,
            'unavailable_chunks': list(unavailable.values()),
            'durability_scope': 'Unclean archive only; normal recovery/native verification still required',
            'world_writes': 0, 'replay_authorized': False}
