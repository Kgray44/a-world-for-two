"""Audit bounded native passenger observations; never drive or simulate a ride.

Point observations cannot exclude teleports between captures, authenticate player
accounts, prove continuous safety or qualify the wider intended railway route.
Master authenticates the deployed observer and the genuine KG/Sera test session.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
from uuid import UUID
import nbtlib

from control_room.common import UserError
from tools.transport_commission import MILL, ORCHARD, _context, _time, read_observation

STATIONS = ([1332, 71, -994], [1332, 71, -942])
ENTRANCES = ([1331, 71, -991], [1331, 71, -943])
SCOPE = {'dimension': 'minecraft:overworld', 'min_x': 1288, 'max_x': 1350,
         'min_z': -1020, 'max_z': -910}
LIMITS = ('Observed states only. Master must authenticate the native observer, '
          'genuine KG/Sera accounts and absence of external movement. Point captures '
          'cannot prove uninterrupted connections or dismounting from every other vehicle. No continuous '
          'ride safety, zipline braking, wider route, restart, performance, visual '
          'or owner acceptance is inferred.')


def require(condition, message):
    if not condition:
        raise UserError(message)


def identity(value):
    try:
        require(str(UUID(value)) == value, 'Canonical actual UUID required')
    except (ValueError, TypeError, AttributeError) as error:
        raise UserError('Canonical actual UUID required') from error
    return value


def xyz(value):
    require(isinstance(value, list) and len(value) == 3 and all(
        type(n) in (int, float) and math.isfinite(n) for n in value),
        'Actual finite native position required')
    return value


def near(position, target, radius=7):
    return sum((a-b)**2 for a, b in zip(xyz(position), target)) <= radius**2


def series(observations, players, count):
    require(isinstance(observations, list) and len(observations) == count,
            'All ordered native stages are required')
    require(len(players) == 2 and len(set(map(identity, players))) == 2,
            'Distinct authenticated KG and Sera UUIDs required')
    for before, after in zip(observations, observations[1:]):
        _context(before, after, empty=False)
        require(after['game_time'] > before['game_time'], 'Distinct advancing native ticks required')
        require((_time(after['at'])-_time(before['at'])).total_seconds() <= 180,
                'Native passenger stages must be captured within three minutes of each other')
    require((_time(observations[-1]['at'])-_time(observations[0]['at'])).total_seconds() <= 900,
            'Bounded fifteen-minute passenger session required')
    rows = []
    for observation in observations:
        require(observation.get('train_position_scope') == SCOPE,
                'Published Copper Wren observation scope required')
        native = observation['players']
        require(len(native) == 2 and {row.get('uuid') for row in native} == set(players),
                'Both actual connected players must remain present without a replacement')
        indexed = {row['uuid']: row for row in native}
        for row in indexed.values():
            p = xyz(row.get('position'))
            require(row.get('dimension') == 'minecraft:overworld' and
                    row.get('chunk') == [math.floor(p[0]/16), math.floor(p[2]/16)] and
                    type(row.get('health')) in (int, float) and
                    math.isfinite(row['health']) and row['health'] > 0 and
                    type(row.get('hypertube_native_travel')) is bool,
                    'Native dimension/chunk, live health and travel flag required')
        rows.append(indexed)
    return rows


def platform(rows, position):
    require(all(row.get('train_uuid') is None and
                row['hypertube_native_travel'] is False and row.get('on_ground') is True and
                near(row['position'], position) for row in rows.values()),
            'Both players must be observed off-train/off-tube on the arrival platform')


def schedule_contract(snbt):
    """Pinned Create6.0.10 Schedule.write; only its saved Progress may vary."""
    require(isinstance(snbt, str) and 0 < len(snbt) <= 16384, 'Bounded native schedule SNBT required')
    try:
        value = nbtlib.parse_nbt(snbt)
    except (ValueError, TypeError) as error:
        raise UserError('Native schedule SNBT is malformed') from error
    require(isinstance(value, nbtlib.Compound) and set(value) <= {'Cyclic', 'Entries', 'Progress'},
            'Known native schedule compound required')
    if 'Progress' in value:
        require(type(value['Progress']) is nbtlib.Int and 0 <= int(value['Progress']) <= 2,
                'Bounded actual saved schedule progress required')
        del value['Progress']
    entries = []
    for name, count, exact in ((MILL, 2, 1), (ORCHARD, 2, 1), (MILL, 0, 0)):
        entries.append('{Instruction:{Id:"create:destination",Data:{Text:'+json.dumps(name)+'}},'
                       'Conditions:[[{Id:"create:delay",Data:{Value:20,TimeUnit:1}},'
                       '{Id:"create:player_count",Data:{Count:'+str(count)+',Exact:'+str(exact)+'}}]]}')
    expected = nbtlib.parse_nbt('{Cyclic:0b,Entries:['+','.join(entries)+']}')
    require(value == expected, 'Exact finite Mill/Orchard/Mill dwell and player conditions required')
    return value


def stations(observation):
    rows = observation.get('stations')
    require(isinstance(rows, list) and len(rows) == 2, 'Both actual station attachments required')
    for row, position, name in zip(rows, STATIONS, (MILL, ORCHARD)):
        require(row.get('position') == position and row.get('available') is True and
                row.get('name') == name and row.get('station_point') is True and
                row.get('valid_track') is True and row.get('graph_id'),
                'Named native station/track attachment required')
        identity(row.get('station_uuid'))
    require(rows[0]['station_uuid'] != rows[1]['station_uuid'] and
            rows[0]['graph_id'] == rows[1]['graph_id'] and
            observation.get('track_graph', {}).get('status') == 'station_nodes_connected' and
            observation['track_graph'].get('graph_id') == rows[0]['graph_id'],
            'Both distinct stations must share a connected actual graph')
    return rows


def train_round_trip(observations, players):
    """Seven stages: platform, boarded, outbound, halt, inbound, mill, unloaded."""
    riders = series(observations, players, 7)
    native_stations = [stations(observation) for observation in observations]
    reference = [(row['station_uuid'], row['graph_id']) for row in native_stations[0]]
    require(all([(row['station_uuid'], row['graph_id']) for row in rows] == reference
                for rows in native_stations), 'Station/graph identities changed during the trip')
    mounted = {riders[1][player].get('train_uuid') for player in players}
    require(len(mounted) == 1, 'Both players must board the same native train')
    train_id = identity(mounted.pop())
    trains = []
    for observation in observations:
        rows = observation.get('trains')
        require(isinstance(rows, list) and len({row.get('uuid') for row in rows}) == len(rows),
                'Unambiguous native train registry required')
        selected = [row for row in rows if row.get('uuid') == train_id]
        require(len(selected) == 1, 'Same actual train must be observed at every stage')
        train = selected[0]
        require(train.get('invalid') is False and train.get('derailed') is False and
                train.get('double_ended') is True and train.get('forward_conductor') is True and
                train.get('backward_conductor') is True and train.get('carriages') == 1 and
                isinstance(train.get('seats'), list) and len(train['seats']) == 1 and
                type(train['seats'][0]) is int and train['seats'][0] >= 3 and
                train.get('graph_id') == reference[0][1] and
                train.get('schedule_present') is True and train.get('schedule_cyclic') is False and
                isinstance(train.get('native_schedule_snbt'), str) and train['native_schedule_snbt'] and
                type(train.get('speed')) in (int, float) and math.isfinite(train['speed']),
                'Actual double-ended conducted train and finite schedule required')
        xyz(train.get('position'))
        schedule_contract(train['native_schedule_snbt'])
        trains.append(train)
    require([row.get('schedule_entry') for row in trains] == [0, 0, 1, 1, 2, 2, 0] and
            all(row.get('schedule_completed') is False for row in trains[:6]),
            'Actual native schedule entry progression must match the finite round trip')
    platform(riders[0], STATIONS[0])
    platform(riders[6], STATIONS[0])
    for n in range(1, 6):
        require(trains[n].get('player_passengers') == 2 and all(
            row.get('train_uuid') == train_id and row['hypertube_native_travel'] is False
            and near(row['position'], trains[n]['position'], 16) for row in riders[n].values()),
            'Both actual players must remain mounted on the observed carriage')
    for n, station_index, name in ((1, 0, MILL), (3, 1, ORCHARD), (5, 0, MILL)):
        require(abs(trains[n]['speed']) <= .001 and trains[n].get('station') == name and
                native_stations[n][station_index].get('present_train') == train_id and
                near(trains[n]['position'], STATIONS[station_index], 16),
                'Actual stationary attachment at every scheduled stop required')
    for n in (2, 4):
        require(abs(trains[n]['speed']) > .001 and trains[n].get('station') is None and
                trains[n].get('schedule_paused') is False and
                trains[n].get('schedule_completed') is False,
                'Native scheduled motion must be observed in both directions')
    zs = [row['position'][2] for row in trains]
    require(zs[1]+8 <= zs[2] <= zs[3]-8 and zs[5]+8 <= zs[4] <= zs[3]-8,
            'Both moving observations must lie between the actual named stops')
    require(trains[0].get('player_passengers') == 0 and trains[6].get('player_passengers') == 0 and
            abs(trains[6]['speed']) <= .001 and trains[6].get('station') == MILL and
            native_stations[6][0].get('present_train') == train_id and
            trains[6].get('schedule_completed') is True and trains[6].get('schedule_paused') is True,
            'Finite schedule must finish parked at the mill with both players unloaded')
    return {'format': 'awft-passenger-observation-audit:1', 'system': 'train', 'passed': True,
            'observed_train_uuid': train_id, 'observed_player_uuids': list(players),
            'observed_station_separation_m': 52, 'observations': 7, 'evidence_scope': LIMITS}


def tube_links(observation):
    rows = observation.get('tube_links')
    require(isinstance(rows, list) and len(rows) == 6, 'Six actual tube links required')
    result = []
    for n, row in enumerate(rows):
        require(row.get('available') is True and row.get('stored_reciprocal') is True and
                row.get('from') == [1331, 71, -991+8*n] and
                row.get('to') == [1331, 71, -983+8*n] and row.get('distance') == 8,
                'Actual reciprocal eight-metre tube links required')
        result.append(identity(row.get('uuid')))
    require(len(set(result)) == 6, 'Distinct actual tube links required')
    return result


def tube_round_trip(observations, players):
    """Eight stages: ground/in-tube/in-tube/ground, then the reverse direction."""
    riders = series(observations, players, 8)
    links = [tube_links(observation) for observation in observations]
    require(all(row == links[0] for row in links), 'Stored tube identity changed during travel')
    for base, start, end, sign in ((0, ENTRANCES[0], ENTRANCES[1], 1),
                                  (4, ENTRANCES[1], ENTRANCES[0], -1)):
        platform(riders[base], start)
        platform(riders[base+3], end)
        for player in players:
            first, second = riders[base+1][player], riders[base+2][player]
            require(first['hypertube_native_travel'] is True and second['hypertube_native_travel'] is True and
                    first.get('train_uuid') is None and second.get('train_uuid') is None and
                    first['chunk'][1] != second['chunk'][1] and
                    sign*(second['position'][2]-first['position'][2]) >= 8,
                    'Native tube travel across an actual chunk boundary required in each direction')
            for row in (first, second):
                x, y, z = row['position']
                require(abs(x-1331) <= 4 and abs(y-71) <= 4 and -991 < z < -943,
                        'Actual in-tube position must lie inside the retained span')
            require(riders[base+3][player]['health'] >= riders[base][player]['health'],
                    'Observed arrival health decreased; investigate before acceptance')
    return {'format': 'awft-passenger-observation-audit:1', 'system': 'hypertube', 'passed': True,
            'observed_player_uuids': list(players), 'observed_stored_link_uuids': links[0],
            'observations': 8, 'evidence_scope': LIMITS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('system', choices=('train', 'hypertube'))
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--kg-uuid', required=True)
    parser.add_argument('--sera-uuid', required=True)
    parser.add_argument('observations', nargs='+', type=Path)
    args = parser.parse_args()
    count = 7 if args.system == 'train' else 8
    require(len(args.observations) == count, 'Exact finite observation stage count required')
    parent = args.home.resolve(strict=True)/'dashboard/settlement'
    documents, references = [], []
    for path in args.observations:
        path = path.resolve(strict=True)
        require(path.parent == parent and re.fullmatch(
            r'transport-observation-result-[a-f0-9-]{36}\.json', path.name),
            'Canonical native observation family under the declared home required')
        document, digest = read_observation(path)
        require(Path(document.get('world', '')).resolve() == args.home.resolve()/'world/RosewaterArtistic',
                'Actual observation world must match the declared construction home')
        documents.append(document)
        references.append({'path': str(path), 'sha256': digest})
    audit = train_round_trip if args.system == 'train' else tube_round_trip
    result = audit(documents, [args.kg_uuid, args.sera_uuid])
    result['native_observation_references'] = references
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
