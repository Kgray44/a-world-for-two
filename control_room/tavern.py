"""Bounded Drowned Rose telemetry and explicit existing-console controls.

Adapted from proposals/drowned-rose/dashboard.py. Tavern registrations remain
separate from Native LIFE admissions, villagers and the character registry.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import uuid

from .common import UserError


MAX_AGE_SECONDS = 15


def _read(path, limit):
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Telemetry exceeds its bounded size')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Telemetry must be an object')
    return value


class Tavern:
    def __init__(self, home, send_command):
        self.path = Path(home) / 'dashboard/tavern/status.json'
        self.life_path = Path(home) / 'dashboard/settlement/life-status.json'
        self.send_command = send_command

    def _life_admission(self):
        """A historical admission total, never a live villager/entity census."""
        try:
            value = _read(self.life_path, 512 * 1024)
            count = value.get('projected_managed_population_if_cohort_complete')
            if (value.get('operation') != 'seed' or not value.get('finished')
                    or value.get('failures') != 0 or value.get('error')
                    or value.get('cleanup_passed') is not True or value.get('cleanup_required')
                    or value.get('temporary_tickets_remaining', 0)
                    or value.get('pending_shared_futures', 0)
                    or type(count) is not int or not 0 <= count <= 4000
                    or value.get('spawned', 0) + value.get('existing_preserved', 0) != value.get('members')):
                return None
            return {'registered_total': count, 'at': value['finished'],
                    'scope': 'Last completed Native LIFE admission; not a live census. Tavern NPCs are separate.'}
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def snapshot(self):
        unavailable = {'current': False, 'reason': 'Tavern telemetry unavailable',
                       'residents': [], 'counts': {'registered': None, 'loaded': None, 'roster': None},
                       'max_age_seconds': MAX_AGE_SECONDS, 'life_admission': self._life_admission(),
                       'count_scope': 'Separate Easy NPC tavern registrations; not additional LIFE villagers.'}
        try:
            data = _read(self.path, 128 * 1024)
            rows = data['residents']
            if not isinstance(rows, list) or len(rows) > 45:
                raise ValueError('Invalid bounded resident count')
            identities, ids = set(), set()
            for row in rows:
                if (not isinstance(row, dict) or not isinstance(row.get('id'), str)
                        or not re.fullmatch(r'[a-z][a-z0-9-]{1,48}', row['id'])
                        or row['id'] in ids or type(row.get('loaded')) is not bool
                        or type(row.get('registered')) is not bool):
                    raise ValueError('Invalid resident telemetry')
                ident = str(uuid.UUID(row['uuid']))
                if ident in identities:
                    raise ValueError('Duplicate resident identity')
                identities.add(ident)
                ids.add(row['id'])
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(data['at'].replace('Z', '+00:00'))).total_seconds()
            data.update(current=-2 <= age <= MAX_AGE_SECONDS, age_seconds=age,
                        max_age_seconds=MAX_AGE_SECONDS, life_admission=unavailable['life_admission'],
                        count_scope=unavailable['count_scope'],
                        counts={'registered': sum(r['registered'] for r in rows),
                                'loaded': sum(r['loaded'] for r in rows), 'roster': len(rows)},
                        qualification=('Runtime reports qualification' if data.get('runtime_accepted') is True
                                       else 'Awaiting visual, behavior and audio qualification'))
            if not data['current']:
                data['reason'] = 'Tavern telemetry is stale; counts describe the last report'
            return data
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            return unavailable | {'reason': 'Tavern telemetry missing or invalid; controls unavailable'}

    def control(self, body):
        status = self.snapshot()
        if not status['current'] or not status['counts']['registered']:
            raise UserError('Fresh telemetry with registered tavern residents is required')
        if not isinstance(body, dict):
            raise UserError('A typed tavern action is required')
        action = body.get('action')
        if action == 'music' and set(body) == {'action', 'enabled'} and type(body['enabled']) is bool:
            stop = not body['enabled']
            command = 'awfttavern music ' + str(body['enabled']).lower()
        elif action == 'suspend' and set(body) == {'action', 'suspended'} and type(body['suspended']) is bool:
            stop = body['suspended']
            command = 'awfttavern suspend ' + str(body['suspended']).lower()
        else:
            raise UserError('Choose a boolean music or suspend action')
        if status.get('fault') and not stop:
            raise UserError('Resolve the current tavern fault before resuming')
        self.send_command(command, confirmed=True)
        return {'requested': True, 'runtime_acknowledged': False, 'command': command,
                'note': 'Request sent; the next current telemetry report shows the result.'}
