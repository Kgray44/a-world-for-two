"""Translate authenticated or explicitly assigned character positions into Atlas markers."""
from __future__ import annotations

import math
from datetime import datetime, timezone


def markers(characters, now=None):
    now = datetime.now(timezone.utc).timestamp() if now is None else now
    result = []
    for profile in characters:
        point = profile.get('location') or {}
        observed = point.get('status') == 'live'
        if not all(type(point.get(k)) in (int, float) and math.isfinite(point[k]) for k in ('x', 'y', 'z')):
            point = profile.get('last_known') or profile.get('assigned_location') or {}
            observed = False
        if not all(type(point.get(k)) in (int, float) and math.isfinite(point[k]) and abs(point[k]) <= 30000000 for k in ('x', 'y', 'z')):
            continue
        if point.get('dimension') not in ('minecraft:overworld', 'minecraft:the_nether', 'minecraft:the_end'):
            continue
        try:
            stamp = datetime.fromisoformat((point.get('measured_at') or '').replace('Z', '+00:00'))
            observed = observed and stamp.tzinfo is not None and -2 <= now - stamp.timestamp() <= 30
        except (TypeError, ValueError):
            observed = False
        retained = point.get('status') in ('live', 'last_known') and bool(point.get('measured_at'))
        result.append({**{k: point[k] for k in ('x', 'y', 'z', 'dimension')},
            'id': 'character:' + profile['id'], 'character_id': profile['id'], 'kind': 'character',
            'character_type': profile['kind'], 'name': profile['name'], 'category': 'Characters',
            'district': profile['district'], 'icon': 'pet' if profile['kind'] == 'animal' else 'star',
            'state': 'live' if observed else 'last known' if retained else 'assigned home',
            'at': point.get('measured_at'), 'max_age_seconds': 30})
    return result
