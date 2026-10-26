"""Validate bounded, read-only server chunk-ticket diagnostics."""
import math
import re
from datetime import datetime


def validate(value):
    if not isinstance(value, dict) or not isinstance(value.get('at'), str):
        raise ValueError('Invalid chunk diagnostics')
    datetime.fromisoformat(value['at'].replace('Z', '+00:00'))
    if value.get('unavailable'):
        return {'at': value['at'], 'unavailable': str(value['unavailable'])[:500]}
    dimensions = value.get('dimensions')
    if not isinstance(dimensions, dict) or len(dimensions) > 128:
        raise ValueError('Too many diagnostic dimensions')
    clean = {}
    counters = ('visible_holders', 'full_chunks', 'block_ticking', 'entity_ticking', 'holders_examined', 'pending_unloads', 'vanilla_forced_chunks', 'ticket_positions')
    for name, row in dimensions.items():
        if not re.fullmatch(r'[a-z0-9_.-]+:[a-z0-9_/.-]+', name) or not isinstance(row, dict):
            raise ValueError('Invalid diagnostic dimension')
        current = {}
        for key in counters:
            number = row.get(key)
            if type(number) is not int or not 0 <= number <= 10_000_000:
                raise ValueError('Invalid chunk counter')
            current[key] = number
        details = row.get('details', {})
        if not isinstance(details, dict) or not isinstance(details.get('sources'), list) or len(details['sources']) > 64:
            raise ValueError('Invalid ticket sources')
        sources = []
        for source in details['sources']:
            if not isinstance(source, dict) or not isinstance(source.get('type'), str) or len(source['type']) > 120 or type(source.get('tickets')) is not int or not 0 <= source['tickets'] <= 10_000_000:
                raise ValueError('Invalid ticket source')
            examples = source.get('examples', [])
            if not isinstance(examples, list) or len(examples) > 3:
                raise ValueError('Too many ticket examples')
            for example in examples:
                if not isinstance(example, dict) or not isinstance(example.get('description'), str) or len(example['description']) > 240:
                    raise ValueError('Invalid ticket example')
                for field in ('chunk_x', 'chunk_z', 'level'):
                    if type(example.get(field)) is not int or abs(example[field]) > 10_000_000:
                        raise ValueError('Invalid ticket coordinates')
            sources.append({'type': source['type'], 'tickets': source['tickets'], 'examples': examples})
        elapsed = details.get('measurement_ms')
        levels = details.get('ticket_levels')
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or not 0 <= elapsed <= 10000 or not isinstance(levels, dict) or len(levels) > 128:
            raise ValueError('Invalid diagnostic workload measurements')
        if any(not re.fullmatch(r'-?\d{1,3}', str(k)) or type(v) is not int or not 0 <= v <= 10_000_000 for k, v in levels.items()):
            raise ValueError('Invalid ticket-level histogram')
        mod = details.get('mod_owners', {'owners':[]})
        if not isinstance(mod, dict) or not isinstance(mod.get('owners'), list) or len(mod['owners']) > 64:
            raise ValueError('Invalid mod chunk-ticket owners')
        for owner in mod['owners']:
            if not isinstance(owner, dict) or not re.fullmatch(r'[a-z0-9_.-]+:[a-z0-9_/.-]+', owner.get('controller','')) or owner.get('kind') not in ('block','entity') or not isinstance(owner.get('owner'), str) or len(owner['owner']) > 120 or type(owner.get('ticking')) is not bool or type(owner.get('chunks')) is not int or not 0 <= owner['chunks'] <= 10_000_000:
                raise ValueError('Invalid mod chunk-ticket ownership')
        current['details'] = {'sources': sources, 'ticket_levels': levels, 'truncated': details.get('truncated') is True, 'measurement_ms': elapsed,
            'mod_owners':{'owners':mod['owners'], 'truncated':mod.get('truncated') is True, 'unavailable':str(mod.get('unavailable',''))[:500]}}
        clean[name] = current
    radius = value.get('spawn_chunk_radius')
    if type(radius) is not int or not 0 <= radius <= 32:
        raise ValueError('Invalid spawn chunk radius')
    return {'at': value['at'], 'dimensions': clean, 'spawn_chunk_radius': radius, 'source': str(value.get('source', ''))[:600]}
