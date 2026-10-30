"""One empty ordinary-block hoist request; no placement or game execution.

Inspect the exact cached Create bytecode as data, preserve the frozen Wren plan,
and emit only an explicitly dependent nonexecutable request and VERIFY probes.
Native attachment, mode, stop behavior and entity occupancy remain unproved.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
import re
import subprocess
import zipfile

from control_room.common import UserError, digest, read_json
from tools.grand_harbor_fleet import AIR, build, canonical, identifier
from tools.grand_harbor_berth import (
    HOME, CHECKPOINT, CHECKPOINT_SHA, checked_checkpoint, native_plan, rotate_point,
)
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


HELPER_SHA = 'f61f45913a9d60846bdd6a9d04e6f4a049cfdd0129f1a3d6fc2fec4612cc7984'
FLEET_SHA = 'fe4251af7c032257e15f90a428defb5c523bb51fea8bd09a37db43066958119a'
REGISTRY_SHA = '8cfa5ae77e20b8b5c1730b2928c55156557ebecb7e84480142088bda04ef92c4'
WREN_SOURCE = 'staging/fleet-berth-wren-169d2faf9ba9224f'
WREN_MANIFEST_SHA = '35a1f45207d4b1bef6581b48fb7eb832ed462bc772d9ca893fe755f82e8a69b7'
WREN_AFTER_SHA = '2064645686e03e530d04ba66be8c3074e2617769155bdae5b0dcaca0917d3229'
CREATE_JAR = Path(r'D:\A World for Two\caches\mods\create-1.21.1-6.0.10.jar')
CREATE_SHA = 'ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a'
JAVAP = Path(r'C:\Program Files\Java\jdk-21.0.10\bin\javap.exe')
ORIGIN, ROTATION = (1000, 63, -1366), 1
LOAD = 'minecraft:spruce_planks'
MAX_OUTPUT = 8*1024**2
CLASS_PINS = {
    'com/simibubi/create/content/contraptions/pulley/PulleyBlockEntity.class': 'a2dda7747b7c19a1b23be4190073aad4203ce0bb70d94fd7c514738d4c0a65bd',
    'com/simibubi/create/content/contraptions/pulley/PulleyContraption.class': '23251c328dc9d8d0b5044b855720a97eefc67ccfa6e5032a549ae6d56f525144',
    'com/simibubi/create/content/contraptions/piston/LinearActuatorBlockEntity.class': '46421481e3f650b2c03fa486cf6084f7f320ecc40bbea9d10c699956106ba1aa',
    'com/simibubi/create/content/kinetics/crank/HandCrankBlockEntity.class': 'e05b7f0a4a828502506d1d8490b260ad5d742dd38b7f444f18febbee6da3335c',
    'com/simibubi/create/content/kinetics/crank/HandCrankBlock.class': '6a151f1368fe95ff074dd1b306b6edc3d35f91b197352b5e8bec90b43de250f3',
    'com/simibubi/create/content/kinetics/base/KineticBlockEntity.class': '3bce80f18d09ccff5e6c1b5cdbeeb2793f0a507006879b267148cde0df443572',
    'com/simibubi/create/content/contraptions/Contraption.class': '2f4906644fcf6fbbb99110ae0aafcb39aa427347e6742ea8768a0a24cccf164a',
}
METHODS = {'assemble', 'disassemble', 'visitNewPosition', 'getBlocks', 'getAttachedContraption',
           'tryDisassemble', 'getMovementMode', 'getGridOffset', 'getMovementSpeed',
           'onSpeedChanged', 'turn', 'tick', 'getGeneratedSpeed', 'getRotationSpeed',
           'convertToLinear', 'searchMovedStructure', 'isAnchoringBlockAt'}


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def states(document):
    return {tuple(row[:3]): document['palette'][row[3]] for row in document['blocks']}


def inspect_create(path=CREATE_JAR):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 32*1024**2 or digest(path) != CREATE_SHA:
        raise UserError('Exact cached Create6.0.10 dependency required; no download or execution')
    evidence, files = {}, {}
    with zipfile.ZipFile(path) as archive:
        for name, pin in CLASS_PINS.items():
            if archive.getinfo(name).file_size > 2*1024**2 or hashlib.sha256(archive.read(name)).hexdigest() != pin:
                raise UserError('Pinned native hoist class changed: '+name)
            result = subprocess.run([str(JAVAP), '-classpath', str(path), '-c', '-p', name[:-6].replace('/', '.')],
                                    capture_output=True, text=True, timeout=20,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode or len(result.stdout.encode()) > 512*1024:
                raise UserError('Bounded static bytecode inspection failed: '+name)
            lines = result.stdout.splitlines()
            starts = [i for i, line in enumerate(lines) if line.startswith('  ') and not line.startswith('   ')
                      and '(' in line and line.endswith(';')]
            methods = []
            for n, start in enumerate(starts):
                if any(re.search(r'\b'+method+r'\(', lines[start]) for method in METHODS):
                    methods.append('\n'.join(lines[start:starts[n+1] if n+1 < len(starts) else len(lines)]))
            excerpt = ('Class '+name+'\n\n'+'\n\n'.join(methods)+'\n').encode()
            filename = 'api/'+Path(name).stem+'-javap.txt'
            files[filename] = excerpt
            evidence[name] = {'class_sha256': pin, 'selected_methods': [m.splitlines()[0].strip() for m in methods],
                              'excerpt_sha256': hashlib.sha256(excerpt).hexdigest(), 'excerpt_bytes': len(excerpt)}
    return {'jar_sha256': CREATE_SHA, 'classes': evidence,
            'scope': 'javap reads class bytecode only; no mod class, Minecraft process, world or native motion was executed'}, files


def build_request(registry, snapshot, receipt, template, old_after):
    checked_checkpoint(receipt)
    if (template.get('key') != 'resolute-wren' or old_after.get('backup_sha256') != CHECKPOINT_SHA or
            old_after.get('commands') != [] or old_after.get('world_path') != registry['world_path'] or
            str(old_after.get('seed')) != str(registry['seed'])):
        raise UserError('Exact frozen Wren/current checkpoint dependency required')
    old = states(old_after)
    tags = deepcopy(old_after.get('block_entities', []))
    if len(tags) != 9:
        raise UserError('Preserve the exact nine supplied Wren inventory tags')
    tag_positions = {tuple(row['pos']) for row in tags}
    fitting = next(f for f in template['design']['fittings'] if f['kind'] == 'stopped cargo derrick')
    transform = lambda pos: rotate_point(pos, ORIGIN, ROTATION)
    pulley = transform(fitting['pulley'])
    crank = transform(fitting['local_control'])
    if old.get(pulley) != 'create:rope_pulley[axis=z]' or old.get(crank) != 'create:hand_crank[facing=south,waterlogged=false]':
        raise UserError('Frozen pulley/drive orientation changed; do not alter the drive')
    load = pulley[0], pulley[1]-1, pulley[2]
    if LOAD not in registry['blocks'] or registry['blocks'][LOAD]:
        raise UserError('Ordinary registered non-stateful spruce plank payload required')
    b = fitting['load_sweep_bounds']
    allowed = {transform((x, y, z)) for x in range(b[0], b[3]+1) for y in range(b[1], b[4]+1) for z in range(b[2], b[5]+1)}
    # A single10tick pulse from the unmodified32rpm direct crank has source
    # travel <=0.625block; allow native rounding to the next whole block. This
    # bound is conditional on actual network speed/mode, not measured motion.
    payload_cells = {load, (load[0], load[1]-1, load[2])}
    if not payload_cells <= allowed:
        raise UserError('One-pulse payload path exceeds the frozen load sweep')
    if any(old.get(p) != AIR for p in allowed) or allowed & tag_positions:
        raise UserError('Existing source sweep is occupied or includes inventory/BE')
    neighbors = {(load[0]+dx, load[1]+dy, load[2]+dz) for dx, dy, dz in
                 ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))}
    if any(old.get(p) != AIR for p in neighbors-{pulley}):
        raise UserError('Test payload touches source hull/rail/drive; attachment would be unsafe')
    # Genuinely read the CURRENT ORIGINAL sweep/neighbor states, without
    # treating the prospective Wren or pulley as currently present.
    original = {}
    for pos in sorted(allowed | neighbors | {load}):
        value = snapshot.state(pos)
        if value is None or value != AIR or pos in snapshot.protected:
            raise UserError('Current original hoist volume is occupied/unknown/BE: '+str((pos, value)))
        original[pos] = value
    dependency = {'manifest_source': WREN_SOURCE+'/manifest.json', 'manifest_sha256': WREN_MANIFEST_SHA,
                  'full_after_sha256': WREN_AFTER_SHA, 'actual_native_Wren_completion': None,
                  'requires': 'Master must complete/settle/full-VERIFY Wren, then verify actual current component BEs, untouched storage, native loaded/persistent entity/glue census and exclusive operation lease. Source geometry grants no authority.'}
    request = {
        'format': 'awft-prospective-hoist-request:1', 'execution_forbidden': True, 'construction_forbidden': True,
        'authority': None, 'dependency': dependency, 'name': 'Wren one empty ordinary timber testweight',
        'prospective_payload': [{'pos': list(load), 'state': LOAD}], 'maximum_payload_blocks': 1,
        'payload_BEs_inventories_passengers': 0, 'glue_requested': False,
        'pulley': list(pulley), 'manual_crank': list(crank), 'full_frozen_load_sweep_cells': len(allowed),
        'one_pulse_candidate_payload_cells': [list(p) for p in sorted(payload_cells)],
        'commands': [], 'block_entities': [], 'entities_to_create': [], 'UUIDs_to_allocate': [],
        'scope': 'No drive/rail/hull/config writes, no entity glue, no inventory, boat or player carried. Any native controlled contraption must contain exactly this one ordinary block and no actors/storage/passengers.',
        'source_api_findings': [
            'PulleyBlockEntity.assemble counts existing native ROPE/PULLEY_MAGNET then asks PulleyContraption.assemble at below(floor(offset+1)).',
            'PulleyContraption.assemble uses the native moved-structure search, and the pulley creates a normal ControlledContraptionEntity only for a nonempty moved block map.',
            'The full timber testweight begins directly below the pulley; source neighbors are AIR except the anchoring pulley. Native glue/attachment and actual captured block set still require inspection.',
            'HandCrankBlock rotationSpeed=32; HandCrankBlockEntity.turn sets inUse=10, native tick counts it down and updates generated rotation at0. KineticBlockEntity.convertToLinear divides rpm by512.',
            'Conditional source-only maximum per single unrefreshed pulse is10*32/512=0.625block before grid rounding. Do not treat this as measured speed or a clock-controlled stop guarantee.',
            'LinearActuator.tryDisassemble waits in MOVE_NEVER_PLACE and in MOVE_PLACE_RETURNED away from its initial offset. Actual mode must be read; no default mode is assumed.',
            'Pulley.disassemble grids the offset, uses native contraption disassembly, and may restore native rope/magnet blocks. Never synthesize those states or replay the oldAIR plan as cleanup.',
        ],
        'blockers': [
            'Actual Wren placement/fullAFTER completion and current native palette/BE/kinetic-network proof missing.',
            'Actual rope offset/running/mirror/attachment and movement mode are unknown. Require offset0, stopped unmirrored pulley and no prior moving contraption before choosing this initial-load request.',
            'Native same-tick occupancy/glue/attachment preview and exactly-one-block capture proof are missing; static AIR geometry is insufficient.',
            'Actual one-click32rpm pulse, stop-at-zero behavior, safe parking and normal upper-return disassembly are untested. No automatic input or motion is authorized.',
        ],
        'master_interaction': [
            'Obtain one serialized empty-server construction/inspection lease and actual authorized client/operator slot; exclude all riders and other occupants from the complete native sweep.',
            'Read pulley/crank BEs and actual network: stopped offset0, no mirror/contraption, direct32rpm source capacity, current movement mode. Preserve existing BE/config; do not write Speed/offset/Mode NBT.',
            'Only after current targets, native empty occupancy/glue/attachment and bounded stop conditions are proved may the master separately derive one ordinary-block placement at the requested position. No executable placement is supplied here.',
            'Use one ordinary brief click, released immediately, in the observed lowering direction. Inspect actual native payload map/position/offset and wait for genuine speed0. Abort admission if the expected one-block/zero-storage/zero-passenger set cannot be established safely.',
            'Reverse with one ordinary native opposite input only after the previous pulse stopped and the source/current sweep remains clear. Demonstrate return/park/disassembly using the actual configured native mode; do not delete/teleport a stalled contraption or overwrite native rope blocks.',
            'Record actual entity/block/BE before/after, same ordinary timber identity, released resources, real visual operation and later normal restart. If any condition is unproved, retain the stopped architectural hoist and this blocked request.',
        ],
        'after_semantics': 'Old fullAFTER must pass BEFORE adding a load. A placed testweight/native rope/contraption invalidates its oldAIR assertions. After motion, build an observed exact VERIFY view; never PLACE/replay the old after plan or its stock tags to reset the scene. If the separate ladder addon was placed, compose its admitted AFTER into master preflight and preserve it.',
        'runtime_motion_stop_restart_acceptance': 'UNVERIFIED; no successful lift is claimed',
    }
    prospective_probe = {p: old[p] for p in allowed | neighbors | {pulley, crank}}
    return {
        'request': request,
        'current_original': native_plan(registry, original, 'Current saved6ad3a8 ORIGINAL hoist volume VERIFY ONLY'),
        'prospective_support': native_plan(registry, prospective_probe, 'PROSPECTIVE Wren hoist sweep and connected components VERIFY ONLY'),
        'preservation': {'existing_Wren_BE_tags': len(tags), 'existing_BE_tags_sha256': sha(tags),
                         'existing_BE_or_inventory_writes': 0, 'source_component_or_rail_writes': 0,
                         'actual_current_Wren_hull': 'NOT ASSERTED', 'executable_PLACEMENT_emitted': False},
    }


def prepare(home=HOME, output=None):
    home = Path(home).resolve()
    if home != HOME.resolve():
        raise UserError('One existing construction home only')
    for name, pin in (('grand_harbor_berth.py', HELPER_SHA), ('grand_harbor_fleet.py', FLEET_SHA)):
        if digest(Path(__file__).with_name(name)) != pin:
            raise UserError('Frozen Wren hoist source changed')
    receipt = read_json(home/'dashboard/settlement/backup-receipt.json', {})
    checked_checkpoint(receipt)
    reg_path = home/'staging/fleet-registry-provenance-8cfa5ae7/registry-original.json'
    if digest(reg_path) != REGISTRY_SHA:
        raise UserError('Historical native registry source changed')
    registry = read_json(reg_path)
    folder = home/WREN_SOURCE
    if digest(folder/'manifest.json') != WREN_MANIFEST_SHA or digest(folder/'complete-after-VERIFY-ONLY.json') != WREN_AFTER_SHA:
        raise UserError('Exact Wren dependency changed')
    api, api_files = inspect_create()
    snapshot = BackupWorld(home, receipt, registry)
    try:
        result = build_request(registry, snapshot, receipt, build(registry, 'resolute-wren'), read_json(folder/'complete-after-VERIFY-ONLY.json'))
        sources = snapshot.sources[:]
    finally:
        snapshot.close()
    checked_checkpoint(read_json(home/'dashboard/settlement/backup-receipt.json', {}))
    files = api_files | {
        'request-NONEXECUTABLE.json': canonical(result['request']),
        'current-original-volume-VERIFY-ONLY.json': canonical(result['current_original']),
        'prospective-support-VERIFY-ONLY.json': canonical(result['prospective_support']),
        'native-api-evidence.json': canonical(api),
    }
    manifest = {'format': 'awft-fleet-hoist-demo-proposal:1', 'checkpoint_id': CHECKPOINT,
                'checkpoint_sha256': CHECKPOINT_SHA, 'source_sha256': digest(Path(__file__)),
                'frozen_Wren_helper_sha256': HELPER_SHA, 'frozen_fleet_sha256': FLEET_SHA,
                'historical_registry_sha256': REGISTRY_SHA, 'current_native_palette': 'PENDING MASTER',
                'preservation': result['preservation'], 'dependency': result['request']['dependency'],
                'saved_region_sources': sources,
                'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in files.items()},
                'native_calls': 0, 'world_writes': 0, 'mod_classes_executed': 0,
                'status': 'BLOCKED NONEXECUTABLE REQUEST ONLY; no cargo hoist operation/acceptance',
                'monitoring': '30GiB separately per drive; monitoring does not constrain external apps or existing writers'}
    output = Path(output).resolve() if output else home/'staging'/('fleet-hoist-'+sha(manifest)[:16])
    if output.exists() or not output.is_relative_to(home/'staging') or not output.name.startswith('fleet-hoist-'):
        raise UserError('Unique owned fleet-hoist output required')
    files['manifest.json'] = canonical(manifest)
    if sum(map(len, files.values())) > MAX_OUTPUT:
        raise UserError('Combined hoist request/API evidence exceeds8MiB')
    guard(0, MAX_OUTPUT)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return {'directory': str(output), 'manifest_sha256': digest(output/'manifest.json'),
            'bytes': sum(map(len, files.values())), 'payload': result['request']['prospective_payload'],
            'status': manifest['status'], 'native_calls': 0, 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=HOME)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    import json
    print(json.dumps(prepare(args.home, args.output)))
