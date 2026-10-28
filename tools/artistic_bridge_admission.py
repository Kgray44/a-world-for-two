"""Bind exact authored glue retirement to immutable saves and native receipts.

Preparation and binding write private evidence only. Neither launches Minecraft,
changes an entity/world, installs a plan nor invokes a native operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import uuid
import zipfile
import zlib

from control_room.common import UserError, digest, read_json
from tools.artistic_bridge_refinement import MASTER_SHA, encoded, flatten, payload
from tools.artistic_engineering import checked_native_proof
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, MAX_CHUNK, NBTReader

MIB = 1024**2
MAX_OUTPUT = 8*MIB
ORIGIN_ID = '20261027T165546Z-56af9a'
ORIGIN_SHA = '15ecf2148c90a994005170398232392e59a83d963b19e63de915d4d745ea1643'
PRE_ID = '20261027T093048Z-eafdca'
PRE_SHA = 'a9d481b7e48d19b449e5e3784d31f0ee5d61d119cd7124736486cbc4763bd067'
POST_ID = '20261027T105419Z-7e0e28'
POST_SHA = 'c32a043d5ef1d2da36ffcc3b9b84c1b283d0d9c4a1b7a9dc211180d73d24294c'
CYCLE_NAME = 'engineering-result-2fae1ceb-ae51-461b-82b2-2822e8ce3717.json'
CYCLE_SHA = '95c4d8d4db2d464acfbe26971c56eb22f19f13ff4949ee669160982f701ba1b8'
ENGINEERING_SHA = '5944d3e7acbf93d11930ee055071e2c12c71f50335920d6da7b09c8ad5b370cd'
CREATE_SHA = 'ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a'
REFINEMENT_MANIFEST_SHA = 'b71b99211b0b89010a9670b8a6d0091eadd234f4d554fc6daa30266022562326'
ORIGINAL_PROPOSAL_PHYSICAL_SHA = '824db735a30f7329e5271ae3237d122b8a279279f76b818f4cd8f2ca84bf3bbe'
ORIGINAL_ENGINEERING_SHA = 'd7c11bf39980a861cc2f8a04a9b4ca334fd6b273cd955223cc71fffb7f234e1e'
NEW_PHYSICAL_SHA = '82778b15dc4139ed149df2c26adb67dc93ff92a6c9fd5a8d33b103d0d4915404'
ORIGIN_PROVENANCE_SHA = 'dedfb17410b01b5996cdde1957e5f30a5f96f54a09f00cd28515da87bbf52453'
OLD_BOXES = ((1187., 69., -1172., 1199., 75., -1143.),
             (1187., 69., -1143., 1199., 75., -1115.))
JAVA_SOURCE = Path('compat/bridge-refinement-admission/RefinementGlueAdmission.java')


def canonical_bytes(document):
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


class TypedNBTReader(NBTReader):
    """Original typed value tree; float/double raw bits and empty-list types survive."""
    def value(self, kind, depth=0):
        self.nodes += 1
        if depth > 48 or self.nodes > 300000:
            raise UserError('Typed NBT exceeds its finite node/depth bound')
        if kind in (1, 2, 3, 4): value = self.number({1: 'b', 2: 'h', 3: 'i', 4: 'q'}[kind])
        elif kind in (5, 6): value = self.take(4 if kind == 5 else 8).hex()
        elif kind == 8: value = self.string()
        elif kind in (7, 11, 12):
            count = self.number('i'); size, code = {7: (1, 'b'), 11: (4, 'i'), 12: (8, 'q')}[kind]
            if count < 0 or count*size > MAX_CHUNK: raise UserError('Typed NBT array exceeds bound')
            value = list(struct.unpack('>'+str(count)+code, self.take(count*size)))
        elif kind == 9:
            subtype, count = self.number('B'), self.number('i')
            if count < 0 or count > 100000 or count and subtype == 0: raise UserError('Invalid typed NBT list')
            value = {'element_type': subtype, 'values': [self.value(subtype, depth+1) for _ in range(count)]}
        elif kind == 10:
            value = {}
            while True:
                child = self.number('B')
                if child == 0: break
                name = self.string()
                if name in value: raise UserError('Duplicate typed compound member')
                value[name] = self.value(child, depth+1)
        else: raise UserError('Unsupported typed NBT kind')
        return [kind, value]


def entity_chunk_record(raw, sector, count, expected_chunk):
    """Read one complete native entity record, including valid unpadded EOF.

    RegionFile may leave the final allocated sector physically unpadded. Only
    its unused tail is optional: header, declared payload, EOF and NBT remain
    mandatory. No file is padded, extracted, repaired or changed here.
    """
    offset = sector*4096
    rounded_end = ((len(raw)+4095)//4096)*4096
    if sector < 2 or not count or (sector+count)*4096 > rounded_end or offset+5 > len(raw):
        raise UserError('Bad entity region sector')
    length = int.from_bytes(raw[offset:offset+4], 'big')
    if not 1 < length <= count*4096-4 or offset+4+length > len(raw):
        raise UserError('Bad or incomplete entity chunk length')
    mode, packed = raw[offset+4], raw[offset+5:offset+4+length]
    if mode not in (1, 2, 3):
        raise UserError('Unsupported entity compression')
    if mode == 3:
        decoded = packed
    else:
        decoder = zlib.decompressobj(31 if mode == 1 else 15)
        decoded = decoder.decompress(packed, MAX_CHUNK+1)
        if decoder.unconsumed_tail or decoder.unused_data or not decoder.eof:
            raise UserError('Entity chunk exceeds bound, has trailing compressed data or is truncated')
    if len(decoded) > MAX_CHUNK:
        raise UserError('Entity chunk exceeds bound')
    plain, typed = NBTReader(decoded).read(), TypedNBTReader(decoded).read()
    if (plain.get('DataVersion') != 3955 or plain.get('Position') != list(expected_chunk)
            or typed[1].get('DataVersion') != [3, 3955]
            or typed[1].get('Position') != [11, list(expected_chunk)]):
        raise UserError('Exact native entity chunk coordinates, types and DataVersion3955 required')
    return plain, typed


def saved_glue(home, registry, checkpoint_id, checkpoint_sha):
    """Authenticate complete ZIP and bounded entity members; no live MCA access."""
    path = home/'backups'/(checkpoint_id+'.zip')
    if not path.is_file() or path.stat().st_size > 512*MIB or digest(path) != checkpoint_sha:
        raise UserError('Exact bounded immutable checkpoint ZIP required')
    companion = read_json(path.with_suffix('.json'))
    if companion.get('integrity') != 'verified' or companion.get('sha256') != checkpoint_sha:
        raise UserError('The backup companion is not verified')
    prefix = Path(registry['world_path']).resolve().relative_to(home).as_posix()+'/entities/'
    glues, sources = [], []
    with zipfile.ZipFile(path) as archive:
        if archive.getinfo('awft-backup.json').file_size > 8*MIB: raise UserError('Unbounded backup index')
        manifest = json.loads(archive.read('awft-backup.json'))
        records = [row for row in manifest['files'] if row['path'].startswith(prefix) and row['path'].endswith('.mca')]
        if len(records) > 16 or sum(row['size'] for row in records) > 32*MIB:
            raise UserError('Saved entity audit exceeds its finite allocation')
        for record in sorted(records, key=lambda v: v['path']):
            raw = archive.read(record['path'])
            if len(raw) != record['size'] or hashlib.sha256(raw).hexdigest() != record['sha256']:
                raise UserError('Entity region size/digest differs')
            sources.append({'path': record['path'], 'sha256': record['sha256'], 'bytes': record['size']})
            # Minecraft can retain a newly created zero-byte entity region with
            # no saved chunks. Any nonempty truncated header remains a failure.
            if len(raw) == 0: continue
            if len(raw) < 8192: raise UserError('Truncated nonempty entity region header')
            region_name = re.fullmatch(r'r\.(-?\d+)\.(-?\d+)\.mca', Path(record['path']).name)
            if region_name is None: raise UserError('Exact native entity region filename required')
            rx, rz = map(int, region_name.groups())
            for slot in range(1024):
                loc = int.from_bytes(raw[4*slot:4*slot+4], 'big'); sector, count = loc >> 8, loc & 255
                if not loc: continue
                expected_chunk = (rx*32+(slot&31), rz*32+(slot>>5))
                plain, typed = entity_chunk_record(raw, sector, count, expected_chunk)
                entries = plain.get('Entities', [])
                typed_entries = typed[1].get('Entities', [9, {'values': []}])[1]['values']
                if len(entries) != len(typed_entries): raise UserError('Typed/untyped entity inventory differs')
                for entity, tag in zip(entries, typed_entries):
                    if entity.get('id') != 'create:super_glue': continue
                    numbers = entity.get('UUID', [])
                    if len(numbers) != 4: raise UserError('Saved glue lacks a complete native UUID')
                    ident = str(uuid.UUID(bytes=b''.join((v & 0xffffffff).to_bytes(4, 'big') for v in numbers)))
                    pos, lower, upper = (entity.get(k, []) for k in ('Pos', 'From', 'To'))
                    if any(len(v) != 3 for v in (pos, lower, upper)): raise UserError('Saved glue lacks exact native bounds')
                    box = tuple(pos[i]+lower[i] for i in range(3))+tuple(pos[i]+upper[i] for i in range(3))
                    glues.append({'uuid': ident, 'entity_id': entity['id'], 'bounds': list(box), 'position': pos,
                                  'canonical_nbt': tag, 'canonical_nbt_sha256': hashlib.sha256(canonical_bytes(tag)).hexdigest()})
    if len({v['uuid'] for v in glues}) != len(glues): raise UserError('Duplicate saved glue UUID')
    return glues, sources


def by_old_leaf(glues):
    # This stage has two authored glues total. Unknown/extra saved glue is never
    # classified as ours merely because it overlaps or resembles a leaf box.
    if len(glues) != 2: raise UserError('Exactly two known saved glue entities required; preserve extras')
    result = []
    for box in OLD_BOXES:
        matches = [row for row in glues if tuple(row['bounds']) == box]
        if len(matches) != 1: raise UserError('Known glue inventory/bounds differ')
        result.append(matches[0])
    return result


def build_origin(home, registry):
    engineering = home/'staging/bascule-restart-cycle-20261027T0926/engineering-contained.json'
    if digest(engineering) != ENGINEERING_SHA:
        raise UserError('Exact authored historical engineering plan required')
    historical = read_json(engineering)
    boxes = [tuple(row['glue_min'])+tuple(v+1 for v in row['glue_max']) for row in historical['systems']]
    if historical.get('construction_sha256') != MASTER_SHA or historical.get('open_angle_degrees') != 55 or tuple(boxes) != OLD_BOXES:
        raise UserError('Historical native program does not identify the old authored leaf volumes')
    pre, pre_sources = saved_glue(home, registry, PRE_ID, PRE_SHA)
    post, post_sources = saved_glue(home, registry, POST_ID, POST_SHA)
    current, current_sources = saved_glue(home, registry, ORIGIN_ID, ORIGIN_SHA)
    pre, post, current = map(by_old_leaf, (pre, post, current))
    cycle = home/'dashboard/settlement'/CYCLE_NAME
    if digest(cycle) != CYCLE_SHA or cycle.with_name(cycle.name+'.complete').read_text().strip() != CYCLE_SHA:
        raise UserError('Exact immutable native two-cycle receipt and marker required')
    receipt = read_json(cycle)
    if (receipt.get('operation') != 'commission' or receipt.get('plan_sha256') != ENGINEERING_SHA
            or receipt.get('cycles') != 2 or receipt.get('cleanup_required') is not False
            or receipt.get('temporary_tickets_remaining') != 0 or receipt.get('error')):
        raise UserError('The historical native cycle did not finish with complete cleanup')
    result = []
    for index, (a, b, c) in enumerate(zip(pre, post, current)):
        if b['uuid'] != c['uuid'] or b['canonical_nbt'] != c['canonical_nbt'] or a['uuid'] == b['uuid']:
            raise UserError('Exact post-cycle UUID/NBT continuity into checkpoint38 is not established')
        result.append(dict(c, name='north' if index == 0 else 'south', previous_cycle_uuid=a['uuid'],
                           post_cycle_canonical_nbt_sha256=b['canonical_nbt_sha256']))
    return {'format': 'awft-refinement-glue-origin:1', 'old_physical_sha256': MASTER_SHA,
            'pinned_create_sha256': CREATE_SHA, 'historical_engineering_sha256': ENGINEERING_SHA,
            'native_cycle_sha256': CYCLE_SHA, 'native_cycle_finished': receipt['finished'],
            'pre_cycle_checkpoint': {'id': PRE_ID, 'sha256': PRE_SHA, 'entity_sources': pre_sources},
            'post_cycle_checkpoint': {'id': POST_ID, 'sha256': POST_SHA, 'entity_sources': post_sources},
            'origin_checkpoint': {'id': ORIGIN_ID, 'sha256': ORIGIN_SHA, 'entity_sources': current_sources},
            'ownership': 'Exact two UUIDs and complete typed NBT persist from the first verified stopped save after the authored native cycles into checkpoint38; pinned Create captures AABBs and recreates fresh UUID entities on disassembly',
            'glues': result}


def prepare(home, proposal, full_verification, output, checkpoint_id, checkpoint_sha):
    home, proposal, full_verification, output = map(lambda p: Path(p).resolve(), (home, proposal, full_verification, output))
    if (not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')) or output.exists()
            or not output.is_relative_to(home/'staging')):
        raise UserError('New private artistic admission output required')
    reserve = guard(4*MIB, MAX_OUTPUT)
    if (digest(proposal/'manifest.json') != REFINEMENT_MANIFEST_SHA
            or digest(proposal/'full-verification.json') != ORIGINAL_PROPOSAL_PHYSICAL_SHA
            or digest(proposal/'engineering-PROPOSAL.json') != ORIGINAL_ENGINEERING_SHA
            or digest(full_verification) != NEW_PHYSICAL_SHA):
        raise UserError('Exact frozen bridge refinement proposal required')
    current = read_json(home/'dashboard/settlement/backup-receipt.json')
    if current.get('verified') is not True or current.get('id') != checkpoint_id or current.get('sha256') != checkpoint_sha:
        raise UserError('Exact current verified stopped checkpoint required')
    registry = read_json(home/'dashboard/settlement/registry.json')
    if digest(home/'server/mods/create-1.21.1-6.0.10.jar') != CREATE_SHA: raise UserError('Pinned native Create artifact differs')
    origin = build_origin(home, registry)
    if hashlib.sha256(encoded(origin)).hexdigest() != ORIGIN_PROVENANCE_SHA:
        raise UserError('Exact reviewed native entity provenance changed')
    glues, _ = saved_glue(home, registry, checkpoint_id, checkpoint_sha)
    if by_old_leaf(glues) != [{k: v for k, v in row.items() if k not in ('name', 'previous_cycle_uuid', 'post_cycle_canonical_nbt_sha256')} for row in origin['glues']]:
        raise UserError('Current saved glue differs from positively identified checkpoint38 entities')
    template = read_json(proposal/'native-before.json'); old = flatten(template)
    moving = flatten(read_json(proposal/'moving-delta.json'))
    if len(moving) != 1130 or not set(moving) <= set(old): raise UserError('Exact moving preimage inventory required')
    snapshot = BackupWorld(home, current, registry)
    try:
        actual = {pos: snapshot.state(pos) for pos in moving}
        if set(actual) & snapshot.protected: raise UserError('Preserve saved BE in the moving preimage')
        # The saved actual preimage must retain the admitted original identities
        # and orientations. Derived connections are measured, never guessed.
        from tools.artistic_bridge_refinement import same_authored_intent
        if any(not same_authored_intent(old[pos], actual[pos]) for pos in moving):
            raise UserError('The saved moving leaf differs from the admitted original preimage')
    finally: snapshot.close()
    future_full = read_json(full_verification); future_full['backup_sha256'] = checkpoint_sha
    future_sha = hashlib.sha256(encoded(future_full)).hexdigest()
    future_engineering = read_json(proposal/'engineering-PROPOSAL.json')
    future_engineering.update(backup_sha256=checkpoint_sha, construction_sha256=future_sha)
    docs = {'glue-origin.json': origin,
            'moving-preimage.json': payload(template, actual, checkpoint_sha, 'VERIFY ONLY - exact moving leaf preimage before authored glue retirement'),
            'new-full-verification.json': future_full,
            'engineering-after-retirement.json': future_engineering}
    raw = {name: encoded(doc) for name, doc in docs.items()}
    index = {'format': 'awft-refinement-glue-prepared:1', 'checkpoint_id': checkpoint_id, 'checkpoint_sha256': checkpoint_sha,
             'new_physical_sha256': NEW_PHYSICAL_SHA, 'origin_sha256': hashlib.sha256(raw['glue-origin.json']).hexdigest(),
             'new_full_base_path': str(full_verification.relative_to(home)),
             'engineering_base_path': str((proposal/'engineering-PROPOSAL.json').relative_to(home)),
             'current_new_physical_sha256': future_sha,
             'moving_preimage_sha256': hashlib.sha256(raw['moving-preimage.json']).hexdigest(), 'moving_preimage_blocks': 1130,
             'source_sha256': digest(Path(__file__)), 'reserve_guard': reserve, 'native_actions': False,
             'next_gate': 'Run exact fresh native moving-preimage verification, build the reviewed helper, then bind its actual class/JAR identity; no runtime command issued'}
    raw['prepared.json'] = encoded(index)
    if sum(map(len, raw.values())) > MAX_OUTPUT: raise UserError('Admission preparation exceeds bound')
    output.mkdir(parents=True, exist_ok=False)
    for name, data in raw.items(): (output/name).write_bytes(data)
    return dict(index, output=str(output))


def bind(home, prepared, native_before, bridge_jar, candidate, bridge_version):
    home, prepared, native_before, bridge_jar = map(lambda p: Path(p).resolve(), (home, prepared, native_before, bridge_jar))
    if candidate != '0.1.0-candidate.39' or bridge_version != '0.6.25':
        raise UserError('This isolated proposal is bound to the parent-reviewed candidate39/bridge0.6.25 integration')
    guard(4*MIB, MAX_OUTPUT)
    data = read_json(prepared/'prepared.json')
    current = home/'dashboard/settlement/backup-receipt.json'
    if any(read_json(current).get(k) != data['checkpoint_'+k] for k in ('id', 'sha256')):
        raise UserError('Current checkpoint changed; prepare a new admission')
    if (data.get('origin_sha256') != ORIGIN_PROVENANCE_SHA
            or digest(prepared/'glue-origin.json') != ORIGIN_PROVENANCE_SHA
            or digest(prepared/'moving-preimage.json') != data['moving_preimage_sha256']):
        raise UserError('Prepared immutable inputs changed')
    if digest(home/data['new_full_base_path']) != NEW_PHYSICAL_SHA or digest(prepared/'new-full-verification.json') != data['current_new_physical_sha256']:
        raise UserError('Exact corrected physical base/current references differ')
    expected_full = read_json(home/data['new_full_base_path']); expected_full['backup_sha256'] = data['checkpoint_sha256']
    if expected_full != read_json(prepared/'new-full-verification.json'):
        raise UserError('Only the current checkpoint field may change in the new full geometry')
    proof, marker = checked_native_proof(native_before, data['moving_preimage_sha256'], 1130, maximum_age=300)
    if proof.get('cleanup_required') or proof.get('temporary_tickets_remaining', 0) != 0:
        raise UserError('Preimage native operation has pending ticket cleanup')
    if not 0 < bridge_jar.stat().st_size <= 4*MIB: raise UserError('Unbounded bridge artifact')
    import tomllib
    with zipfile.ZipFile(bridge_jar) as jar:
        metadata = tomllib.loads(jar.read('META-INF/neoforge.mods.toml').decode())
        if not any(v.get('modId') == 'awft_control_bridge' and v.get('version') == bridge_version for v in metadata.get('mods', [])):
            raise UserError('Built native bridge metadata differs')
        code = jar.read('worldfortwo/bridge/RefinementGlueAdmission.class')
    def ref(path):
        path = Path(path).resolve()
        if not path.is_relative_to(home) or not 0 < path.stat().st_size <= 512*1024: raise UserError('Bounded home-owned evidence required')
        return {'path': path.relative_to(home).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}
    request = {'format': 'awft-refinement-glue-admission:1', 'candidate': candidate, 'bridge': bridge_version,
               'native_class_sha256': hashlib.sha256(code).hexdigest(), 'bridge_jar_sha256': digest(bridge_jar),
               'checkpoint': ref(current), 'origin': ref(prepared/'glue-origin.json'), 'preimage': ref(prepared/'moving-preimage.json'),
               'new_full_base': ref(home/data['new_full_base_path']), 'new_full_current': ref(prepared/'new-full-verification.json'),
               'native_before': ref(native_before), 'native_before_complete': ref(marker), 'new_physical_sha256': NEW_PHYSICAL_SHA,
               'authority': 'Retire only the two positively identified old authored glue entities; complete live identity/NBT/closed-bearing/exclusive-lease checks required; no geometry/setup/cycles authorized'}
    raw = encoded(request); sha = hashlib.sha256(raw).hexdigest()
    output = home/'dashboard/settlement'/('bridge-refinement-admission-'+sha[:16]); output.mkdir(exist_ok=False)
    (output/'request.json').write_bytes(raw)
    return {'request': str(output/'request.json'), 'sha256': sha, 'native_actions': False}


def engineering(home, prepared, full_plan, native_full, retirement, output, restart=False):
    """Bind initial setup/cycles, or restart commissioning WITHOUT another setup."""
    home, prepared, full_plan, native_full, retirement, output = map(lambda p: Path(p).resolve(),
        (home, prepared, full_plan, native_full, retirement, output))
    if output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('New private engineering admission output required')
    guard(4*MIB, MAX_OUTPUT)
    data = read_json(prepared/'prepared.json')
    origin = read_json(prepared/'glue-origin.json')
    if digest(prepared/'glue-origin.json') != ORIGIN_PROVENANCE_SHA:
        raise UserError('Reviewed original glue provenance differs')
    if not retirement.is_relative_to(home/'dashboard/settlement') or not 0 < retirement.stat().st_size <= 512*1024:
        raise UserError('Actual immutable native retirement receipt required')
    result = read_json(retirement); marker = retirement.with_name(retirement.name+'.complete')
    if not marker.is_file() or marker.read_text().strip() != digest(retirement):
        raise UserError('Retirement completion marker differs')
    old_ids = {row['uuid'] for row in origin['glues']}
    retired = result.get('retired_glues', [])
    if (result.get('operation') != 'retire-old-authored-glue' or result.get('origin_sha256') != ORIGIN_PROVENANCE_SHA
            or result.get('new_physical_base_sha256') != NEW_PHYSICAL_SHA or result.get('retirement_completed') is not True
            or result.get('error') or result.get('cleanup_required') is not False
            or result.get('remaining_owned_tickets') != 0 or result.get('temporary_tickets_remaining') != 0
            or result.get('remaining_loaded_glue_uuids') != []
            or len(retired) != 2 or {row.get('uuid') for row in retired if row.get('removed') is True} != old_ids):
        raise UserError('Exact two-entity native retirement and complete resource cleanup required')
    before_rows = result.get('before_glues', [])
    before = {row['uuid']: row for row in before_rows}
    if len(before_rows) != 2 or len(before) != 2 or any(before.get(row['uuid'], {}).get('canonical_nbt') != row['canonical_nbt']
                              or before.get(row['uuid'], {}).get('canonical_nbt_sha256') != row['canonical_nbt_sha256'] for row in origin['glues']):
        raise UserError('Retirement did not validate both complete original native entities')
    current = read_json(home/'dashboard/settlement/backup-receipt.json')
    base_plan = home/data['new_full_base_path']
    if digest(base_plan) != NEW_PHYSICAL_SHA or current.get('verified') is not True:
        raise UserError('Exact corrected physical base/current verified checkpoint required')
    expected = read_json(base_plan); expected['backup_sha256'] = current['sha256']
    if read_json(full_plan) != expected:
        raise UserError('Full verification plan may change only the current checkpoint SHA')
    physical_sha = digest(full_plan)
    proof, _ = checked_native_proof(native_full, physical_sha, len(expected['blocks']), maximum_age=300)
    if proof.get('cleanup_required') or proof.get('temporary_tickets_remaining', 0) != 0:
        raise UserError('Physical verification has pending cleanup')
    from datetime import datetime
    if datetime.fromisoformat(result['finished'].replace('Z', '+00:00')) > datetime.fromisoformat(proof['started'].replace('Z', '+00:00')):
        raise UserError('Physical verification predates exact glue retirement')
    if restart:
        registry = read_json(home/'dashboard/settlement/registry.json')
        glues, _ = saved_glue(home, registry, current['id'], current['sha256'])
        wanted = {tuple(box[:4])+(74., box[5]) for box in OLD_BOXES}
        if len(glues) != 2 or {tuple(row['bounds']) for row in glues} != wanted or old_ids & {row['uuid'] for row in glues}:
            raise UserError('Restart save must contain exactly two replacement glue volumes at revised maxY73')
        from tools.artistic_bridge_refinement import saved_closed_bearings
        from tools.artistic_mill_orientation import saved_chunk
        snapshot = BackupWorld(home, current, registry)
        try:
            saved_closed_bearings(snapshot)
            for z in (-1172, -1116):
                rows = [row for row in saved_chunk(snapshot, (1203, 70, z)).get('block_entities', [])
                        if (row.get('x'), row.get('y'), row.get('z')) == (1203, 70, z)]
                if len(rows) != 1 or rows[0].get('id') != 'create:sequenced_gearshift': raise UserError('Saved native sequencer missing')
                row = rows[0]; instructions = row.get('Instructions', []); negative = z == -1172
                if (row.get('InstructionIndex') != -1 or row.get('PrevPowered', 0) != 0 or len(instructions) != 4
                        or [v.get('Type') for v in instructions] != ['TURN_ANGLE', 'AWAIT', 'TURN_ANGLE', 'END']
                        or [instructions[n].get('Value') for n in (0, 2)] != [55, 55]
                        or [instructions[n].get('Modifier') for n in (0, 2)] != (['BACK', 'FORWARD'] if negative else ['FORWARD', 'BACK'])):
                    raise UserError('Restart save did not preserve exact idle reversible55 program')
        finally: snapshot.close()
    engineering_base = home/data['engineering_base_path']
    if digest(engineering_base) != ORIGINAL_ENGINEERING_SHA:
        raise UserError('Exact reviewed systems, glue bounds, controls and program required')
    plan = read_json(engineering_base)
    plan.update(backup_sha256=current['sha256'], construction_sha256=physical_sha)
    raw = encoded(plan)
    receipt = {'format': 'awft-refinement-engineering-binding:1', 'engineering_sha256': hashlib.sha256(raw).hexdigest(),
               'physical_sha256': physical_sha, 'native_physical_receipt_sha256': digest(native_full),
               'native_retirement_receipt_sha256': digest(retirement), 'checkpoint_id': current['id'],
               'checkpoint_sha256': current['sha256'], 'restart_without_setup': restart,
               'permitted_parent_sequence': ['commission', 'closed verification'] if restart else ['setup once', 'commission', 'closed verification', 'stop/checkpoint/restart without setup'],
               'native_actions': False}
    output.mkdir(parents=True, exist_ok=False)
    (output/'engineering-plan.json').write_bytes(raw)
    (output/'binding.json').write_bytes(encoded(receipt))
    return dict(receipt, output=str(output))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='operation', required=True)
    a = commands.add_parser('prepare')
    for name in ('home', 'proposal', 'full-verification', 'output'): a.add_argument('--'+name, type=Path, required=True)
    a.add_argument('--checkpoint-id', required=True); a.add_argument('--checkpoint-sha', required=True)
    b = commands.add_parser('bind')
    for name in ('home', 'prepared', 'native-before', 'bridge-jar'): b.add_argument('--'+name, type=Path, required=True)
    b.add_argument('--candidate', required=True); b.add_argument('--bridge-version', required=True)
    c = commands.add_parser('engineering')
    for name in ('home', 'prepared', 'full-plan', 'native-full', 'retirement', 'output'):
        c.add_argument('--'+name, type=Path, required=True)
    c.add_argument('--restart', action='store_true')
    args = vars(parser.parse_args()); operation = args.pop('operation')
    print(json.dumps({'prepare': prepare, 'bind': bind, 'engineering': engineering}[operation](**args), indent=2))
