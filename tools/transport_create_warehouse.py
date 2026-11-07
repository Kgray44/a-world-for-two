"""One eight-block native pneumatic dispatch lane in White Clam Warehouse.

Uses the existing additive shop author and Native plan format. No inventory
stock/filter item, command, runtime adapter or new observation code is created.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import time
import tomllib
import zipfile

from control_room.common import UserError, digest, read_json, utcnow
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld
from tools.transport_create_shops import AIR, MIB, SOURCE_INDEX, SOURCE_INDEX_SHA, artifact_facts, derive, state, witnesses

SOURCE = {'path': 'staging/eastern-shared-roofs-rich-source-1793241266230005000/white-clam-SOURCE-ONLY.json',
          'sha256': '7a5220c5278d887503469929bf4fffb2b3cb1265124d247db8a600b185dd5e3e'}
OVERPRESSURE_SHA = '9c03c26bc50c637dbe1d8b9e19e9c10218687c61d335b36588f11e54805c4cf7'
PINS = {'ItemPumpBlock.class': '9bd0c3192319263adeea81ce8c9df3dbe235c8d0936c934b56ba2ef8da8d99d2',
        'PneumaticConnectionBlock.class': '34cc7a1292f28cd93314257e15d4dca323e1633ce3bd07c2d4e7eaf81b284f1c',
        'PneumaticTubeBlock.class': 'b885858798e33000c0230a04297426d9a395fb17a3a27f1d208d9436262dfc51'}
INPUT, EXTRACT, PUMP, TUBE, INSERT, OUTPUT = tuple((x, 65, -1136) for x in (1319, 1318, 1317, 1316, 1315, 1314))
COG, CRANK = (1317, 65, -1135), (1318, 65, -1135)
MAX_OUTPUT = MIB


def specification(registry):
    def s(name, **props):
        return state(registry, name, **props)
    return {'blocks': {
        INPUT: s('minecraft:barrel', facing='up', open=False),
        EXTRACT: s('overpressure:pneumatic_connection', facing='west', arrow_facing='west', mode='extract', powered=False),
        PUMP: s('overpressure:item_pump', facing='west', waterlogged=False),
        TUBE: s('overpressure:pneumatic_tube', east=True, west=True, north=False, south=False,
                up=False, down=False, waterlogged=False, has_connection=True,
                has_rim=True, has_second_rim=False, rim='west'),
        INSERT: s('overpressure:pneumatic_connection', facing='west', arrow_facing='west', mode='insert', powered=False),
        OUTPUT: s('minecraft:barrel', facing='up', open=False),
        COG: s('create:cogwheel', axis='x', waterlogged=False),
        CRANK: s('create:hand_crank', facing='east', waterlogged=False),
    }, 'stands': [(1319, 65, -1135), (1314, 65, -1135)],
        'extra_air': [(1319, 66, -1136), (1314, 66, -1136)], 'wall_supports': [],
        'inputs_outputs': ['1 plain wheat -> exactly1 same wheat in output',
                           '16 plain wheat -> exactly16 same wheat in output',
                           'after actual wheat filter UI configuration:8 wheat +1 iron input ->8 wheat output +1 iron retained input'],
        'story': 'White Clam Warehouse: genuine pneumatic receiving/dispatch, real cog-driven item pump, actual selectable extraction and two new empty barrels'}


def pneumatic_facts(create_jar, home):
    jar = Path(create_jar).with_name('overpressure-0.1.7.4.jar')
    if digest(jar) != OVERPRESSURE_SHA:
        raise UserError('Exact installed Overpressure0.1.7.4 required')
    with zipfile.ZipFile(jar) as archive:
        for name, sha in PINS.items():
            if hashlib.sha256(archive.read('com/hwmods/overpressure/'+name)).hexdigest() != sha:
                raise UserError('Pinned pump/connection/tube native API changed')
    config = Path(home)/'server/config/overpressure-common.toml'
    values = tomllib.loads(config.read_text(encoding='utf8'))
    if values.get('pneumaticTubes', {}).get('packagersOnly') is not False:
        raise UserError('The current real packagers-only configuration does not admit raw wheat')
    return {'jar_sha256': OVERPRESSURE_SHA, 'class_sha256': PINS, 'actual_config_sha256': digest(config),
            'actual_config_packagersOnly': False, 'pump_rotation_axis': 'facing axisX',
            'pump_drive': 'native small-cog mesh from adjacent same-axis small cog',
            'flow_direction': 'getFlowDirection returns FACING while actual ItemPumpBlockEntity.isRunning; never a fabricated sign-dependent flow',
            'tube_native_rim': 'applyPreferredRim selects WEST functional connector; pump on EAST is not a connection rim; has_connection=true',
            'native_transfer_or_filter_observed': False}


def prepare(home, checkpoint_id, checkpoint_sha, create_jar):
    home = Path(home).resolve()
    if home.parent != Path(r'D:\A World for Two\staging\world-tests').resolve() or not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{6}', checkpoint_id):
        raise UserError('Exact separate construction source checkpoint required')
    reserve = guard(8*MIB, MAX_OUTPUT)
    receipt = read_json(home/'backups'/(checkpoint_id+'.json'))
    if receipt.get('integrity') != 'verified' or receipt.get('sha256') != checkpoint_sha:
        raise UserError('Verified immutable source receipt differs')
    if digest(home/SOURCE_INDEX) != SOURCE_INDEX_SHA or digest(home/SOURCE['path']) != SOURCE['sha256']:
        raise UserError('Exact built39 and warehouse geometry required')
    native = read_json(home/'dashboard/settlement/backup-receipt.json')
    if native.get('verified') is not True or not re.fullmatch('[a-f0-9]{64}', native.get('sha256', '')):
        raise UserError('Separate genuine canonical Native backup identity required')
    registry = read_json(home/'dashboard/settlement/registry.json')
    source = read_json(home/SOURCE['path'])
    spec = specification(registry)
    _, _, _, context = witnesses(spec, source)
    facts = {'create': artifact_facts(create_jar), 'pneumatic': pneumatic_facts(create_jar, home)}
    snapshot = BackupWorld(home, {**receipt, 'id': checkpoint_id, 'verified': True}, registry)
    try:
        actual = {q: snapshot.state(q) for q in sorted(set(spec['blocks']) | context)}
        raw = derive(registry, 'White Clam pneumatic dispatch', spec, source, actual, snapshot.protected, native['sha256'])
        regions = list(snapshot.sources)
    finally:
        snapshot.close()
    manifest = {'format': 'awft-white-clam-native-dispatch-SOURCE:1', 'created': utcnow(),
                'producer_sha256': digest(Path(__file__)), 'shared_shop_source_sha256': digest(Path(__file__).with_name('transport_create_shops.py')),
                'actual_saved_checkpoint': {'id': checkpoint_id, 'sha256': checkpoint_sha},
                'canonical_native_backup_sha256': native['sha256'], 'retained_shop_source': SOURCE,
                'blocks': [[*q, v] for q, v in sorted(spec['blocks'].items())], 'new_AIR_only_cells': len(spec['blocks']),
                'input_barrel': INPUT, 'output_barrel': OUTPUT, 'actual_buffers_to_count': [EXTRACT, PUMP, TUBE, INSERT],
                'real_pump_crank': CRANK, 'operating_feet': spec['stands'], 'input_output_tests': spec['inputs_outputs'],
                'filter_configuration': 'Actual normal Create filter UI with a legitimate wheat sample; no item/filter NBT is authored; filter template is excluded from cargo counts',
                'facts': facts, 'saved_region_sources': regions, 'reserve_guard': reserve,
                'files': {n: {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)} for n, b in raw.items()},
                'required_order': ['Root fresh BEFORE/support', 'one hardware PLACE', 'normal joins', 'strict full AFTER including native modes/rim',
                                   'empty-lane actual crank/pump RPM then actual stop', 'real1wheat transfer with all buffers/counts',
                                   'real16wheat transfer', 'actual wheat filter UI then mixed-input selective extraction',
                                   'drain real transit before stopping; verify actual zero kinetic speed', 'normal save/restart and repeat real transfer'],
                'existing_BE_or_inventory_targets': 0, 'supplied_goods_or_filter_items': 0,
                'native_actions': 0, 'world_writes': 0, 'new_runtime_or_observer': False,
                'status': 'SOURCE ONLY; current native modes/connections/RPM/transfer/sorting/restart/performance remain UNVERIFIED'}
    raw['manifest.json'] = (json.dumps(manifest, separators=(',', ':'))+'\n').encode()
    if sum(map(len, raw.values())) > MAX_OUTPUT:
        raise UserError('Finite1MiB source output exceeded')
    out = home/'staging'/('transport-create-warehouse-'+str(time.time_ns()))
    out.mkdir()
    for name, data in raw.items():
        (out/name).open('xb').write(data)
    return {'folder': str(out), 'manifest_sha256': digest(out/'manifest.json'),
            'bytes': sum(map(len, raw.values())), 'new_cells': len(spec['blocks']), 'native_actions': 0, 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    parser.add_argument('--create-jar', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.checkpoint_id, args.checkpoint_sha, args.create_jar), indent=2))
