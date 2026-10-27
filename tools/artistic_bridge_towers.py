"""Separate fixed-tower artwork; no admission, placement, launch or world writes.

Author against the reviewed future full bridge. Exact current-save binding is a
separate gate after its moving-leaf transaction and native restart cycles.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from control_room.common import UserError, digest, read_json
from tools.artistic_bridge_refinement import AIR, encoded, flatten, leaf_name, payload
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, base, properties

MIB = 1024**2
BASE_SHA = '82778b15dc4139ed149df2c26adb67dc93ff92a6c9fd5a8d33b103d0d4915404'
GEOMETRY_SHA = '5d9eee0c6c0f46bd154b49bd942ef0e9e8ed613a3b7169621cf17de904092141'
FUTURE_SHA = '1bd85d609a3c33ec7c171b6305b4b0cd3550a2a466c08af591ac6be5b57f858d'
CENTERS = (-1178, -1110)
BANK_CENTERS = (-1179, -1109)
MAX_OUTPUT = 8*MIB
CAMERAS = (
    {'name': 'same-north-control-comparison', 'feet': [1180, 72, -1190],
     'yaw': -12.9946165, 'pitch': -18.174744,
     'reference_sha256': '11f444917cf2857f08498bd0c169609c55e3213931b294fdfc139d4879c69f29'},
    {'name': 'north-copper-lantern-silhouette', 'feet': [1166, 76, -1190], 'target': [1182, 85, -1178]},
    {'name': 'south-hip-and-bell', 'feet': [1169, 75, -1121], 'target': [1182, 82, -1110]},
    {'name': 'retained-main-river-view', 'feet': [1168, 64, -1144], 'yaw': -90., 'pitch': -16.4466},
)


class Towers:
    def __init__(self, registry, full):
        self.registry, self.full = registry, full
        self.original = flatten(full)
        self.blocks = dict(self.original)
        self.protected = {tuple(row['pos']) for row in full['block_entities']}
        self.reasons, self.roof_cells = {}, set()
        self.bank_mask = {(1200, y, center+dz) for center in BANK_CENTERS for dz in (-2, 2) for y in range(65, 68)
                          if base(self.original.get((1200, y, center+dz), AIR)) in
                          {'minecraft:stone_bricks', 'minecraft:polished_andesite', 'minecraft:chiseled_stone_bricks',
                           'chipped:small_andesite_bricks', 'chipped:small_stone_bricks', 'chipped:etched_stone_bricks',
                           'chipped:carved_stone', 'chipped:engraved_stone'}}
        for pos, state in self.original.items():
            key = base(state)
            if (leaf_name(pos) or key.startswith(('create:', 'handcrafted:', 'mcwdoors:'))
                    or key in ('minecraft:stone_button', 'minecraft:lantern', 'minecraft:candle', 'minecraft:cartography_table', 'minecraft:bookshelf')
                    or key.startswith('minecraft:potted_')):
                self.protected.add(pos)
            if pos[1] < 82 and key.endswith('_stairs'):
                self.protected.update((pos[0], pos[1]+dy, pos[2]) for dy in (0, 1, 2))
        # Native buttons, supports and radio-adjacent standing/access space.
        for center in CENTERS:
            self.protected.update((x, y, center+3) for x in range(1182, 1190) for y in (71, 72, 73))
            self.protected.update((1182, y, center+dz) for dz in (0, 1, 2) for y in range(70, 74))

    def state(self, key, **props):
        schema = self.registry['blocks'].get(key)
        if schema is None or any(str(value).lower() not in schema.get(name, ()) for name, value in props.items()):
            raise UserError('Unregistered native tower state: '+key+' '+str(props))
        return key+('['+','.join(name+'='+str(value).lower() for name, value in sorted(props.items()))+']' if props else '')

    def put(self, x, y, z, key, *, reason, **props):
        pos = x, y, z
        if pos not in self.bank_mask and not (1178 <= x <= 1187 and 70 <= y <= 96 and any(abs(z-c) <= 5 for c in CENTERS)):
            raise UserError('Outside the two finite fixed tower envelopes')
        state = self.state(key, **props)
        if x == 1187 and (state != AIR or y < 82):
            raise UserError('Only removal of the old east roof lip may reach x1187')
        if pos in self.protected and state != self.original.get(pos, AIR):
            raise UserError('Preserve exact machinery, furnishing, stair headroom, control or BE: '+str(pos))
        self.blocks[pos] = state
        self.reasons[pos] = reason

    def stair(self, x, y, z, key, facing, *, reason, half='bottom'):
        self.put(x, y, z, key, reason=reason, facing=facing, half=half, shape='straight', waterlogged=False)

    def slab(self, x, y, z, key, *, reason, top=False):
        self.put(x, y, z, key, reason=reason, type='top' if top else 'bottom', waterlogged=False)

    def roof(self, x, y, z, facing, surface, *, corner=False):
        # Two original native parts form one ~67-degree two-rise course. Copper
        # end slopes, oxidised flanks and bright standing seams are architectural
        # surfaces, not random block substitutions to satisfy the material rule.
        for dy, stem in ((0, 'roof_low_straight_67_'), (1, 'roof_up_67_')):
            self.put(x, y+dy, z, 'mythrais:'+stem+surface, facing=facing,
                     half='bottom', shape='outer_right' if corner else 'straight', waterlogged=False,
                     reason='native steep copper roof with paired lower/upper course')
            self.roof_cells.add((x, y+dy, z))


def roof_course(p, center, inset, *, half_hip=False):
    xa, xb, za, zb = 1178+inset, 1186-inset, center-5+inset, center+5-inset
    y = 82+2*inset
    for x in range(xa, xb+1):
        for z in range(za, zb+1):
            left, right, front, rear = x == xa, x == xb, z == za, z == zb
            if not (left or right or front or rear): continue
            # The south tower keeps a short half-hip below two decorated attic
            # gables. Its lateral slopes continue to the roof ridge.
            if half_hip and inset >= 2:
                if not (left or right): continue
                front = rear = False
            if left and front: face = 'south'
            elif right and front: face = 'west'
            elif right and rear: face = 'north'
            elif left and rear: face = 'east'
            else: face = 'east' if left else 'west' if right else 'south' if front else 'north'
            corner = (left or right) and (front or rear)
            surface = 'copper' if front or rear else 'bright_copper' if z == center else 'oxidised'
            p.roof(x, y, z, face, surface, corner=corner)


def north_lantern(p, center):
    # Actual three-by-three open lantern, not a solid decorative attic box.
    for x in range(1181, 1184):
        for dz in range(-1, 2):
            corner = x != 1182 and dz != 0
            p.slab(x, 90, center+dz, 'minecraft:waxed_exposed_cut_copper_slab' if corner else 'minecraft:dark_oak_slab',
                   reason='supported cupola collar on the steep hip', top=True)
    for x in (1181, 1183):
        for dz in (-1, 1):
            for y in range(91, 94):
                p.put(x, y, center+dz, 'minecraft:dark_oak_fence', reason='open lantern corner post',
                      north=False, south=False, east=False, west=False, waterlogged=False)
    p.put(1182, 93, center, 'minecraft:lantern', reason='small warm light inside open cupola', hanging=True, waterlogged=False)
    for x in range(1181, 1184):
        for dz in range(-1, 2):
            if x == 1182 and dz == 0: continue
            if x == 1181 and dz == -1: face = 'south'
            elif x == 1183 and dz == -1: face = 'west'
            elif x == 1183 and dz == 1: face = 'north'
            elif x == 1181 and dz == 1: face = 'east'
            else: face = 'east' if x == 1181 else 'west' if x == 1183 else 'south' if dz < 0 else 'north'
            p.roof(x, 94, center+dz, face, 'copper', corner=x != 1182 and dz != 0)
    p.put(1182, 94, center, 'minecraft:waxed_cut_copper', reason='cupola roof crown and lantern support')
    p.put(1182, 95, center, 'mythrais:roof_peak_67_bright_copper', reason='small native copper hip finial', facing='north')


def south_gables_and_bell(p, center):
    for z, face in ((center-3, 'north'), (center+3, 'south')):
        for y in (86, 87):
            for x in range(1181, 1184):
                if (x, y, z) not in p.roof_cells:
                    p.put(x, y, z, 'mythrais:tudorpanel_tan_arch_ellipse_dark_oak', reason='recessed framed half-hip attic gable', facing=face, colour=0)
        for y, row in ((86, 'bot'), (87, 'top')):
            for x, side in ((1182, 'r'), (1183, 'l')):
                p.put(x, y, z, 'mcwwindows:dark_oak_plank_window', reason='actual joined two-wide attic transom', facing='north', part=row+'_'+side)
        p.put(1182, 88, z, 'mythrais:single_gothic_arch_upper_dark_oak', reason='small pointed attic-window arch', facing=face, colour=0, shape='0')
    for z in range(center-2, center+3):
        p.put(1182, 90, z, 'mythrais:roof_cap_67_bright_copper' if z == center else 'mythrais:roof_cap_67_oxidised',
              reason='short half-hip ridge with deliberate central copper saddle', facing='north', half='bottom', shape='straight', waterlogged=False)
    # The vanilla bell hangs from an actual full solid cantilever fixed into the
    # wall. Its own native default BE is created normally; no NBT is injected.
    for x in (1178, 1179):
        p.put(x, 80, center+2, 'chipped:boxed_spruce_planks', reason='solid supported bell-canopy crossbeam')
    p.put(1178, 79, center+2, 'minecraft:bell', reason='actual small native bell under the side canopy', attachment='ceiling', facing='west', powered=False)
    for x in (1178, 1179):
        for dz in (1, 2, 3):
            p.slab(x, 81, center+dz, 'minecraft:waxed_weathered_cut_copper_slab' if dz != 2 else 'minecraft:waxed_exposed_cut_copper_slab',
                   reason='compact shallow copper canopy above the native bell')


def window_bays(p, center):
    front = center-5
    for bottom in (72, 78):
        for x in (1182, 1183):
            p.stair(x, bottom-2, front, 'minecraft:stone_brick_stairs', 'south', half='top', reason='wall-anchored bay corbel')
        for x in range(1181, 1185):
            p.slab(x, bottom-1, front, 'minecraft:waxed_exposed_cut_copper_slab', reason='four-wide supported bay sill', top=True)
        for y, row in ((bottom, 'bot'), (bottom+1, 'top')):
            for x, side in ((1182, 'r'), (1183, 'l')):
                p.put(x, y, center-4, AIR, reason='open the original window into the one-block projecting bay')
                p.put(x, y, front, 'mcwwindows:dark_oak_plank_window', reason='native projecting two-wide shop-like window', facing='north', part=row+'_'+side)
            for x in (1181, 1184):
                p.put(x, y, front, 'mythrais:spiral_column_stone', reason='carved narrow bay jamb', facing='north', colour=1)
        for x in (1181, 1184):
            p.stair(x, bottom+2, front, 'minecraft:stone_brick_stairs', 'east' if x == 1181 else 'west', half='top', reason='layered window-arch shoulder')
        for x in (1182, 1183):
            p.put(x, bottom+2, front, 'mythrais:single_gothic_arch_upper_dark_oak', reason='double pointed bay-window arch detail', facing='north', colour=0, shape='0')
    for x in range(1181, 1185):
        for y in (75, 76):
            p.put(x, y, center-4, 'mythrais:tudorpanel_tan_arch_ellipse_dark_oak' if x in (1181, 1184) else 'mythrais:tudorpanel_tan_arch_double_dark_oak',
                  reason='framed middle-storey panels replace the broad blank plaster panel', facing='north', colour=0)
    for dz in (-2, 2):
        for y in (75, 76):
            p.put(1179, y, center+dz, 'mythrais:tudorpanel_tan_arch_ellipse_dark_oak', reason='side-wall carved recessed panel', facing='west', colour=0)
        p.slab(1178, 74, center+dz, 'minecraft:dark_oak_slab', reason='supported flower ledge on the retained wall band', top=True)
        p.put(1178, 75, center+dz, 'minecraft:potted_cornflower' if center == CENTERS[0] else 'minecraft:potted_allium', reason='contained flower; no tree or uncontrolled growth')
    for dz in (-3, 3):
        p.put(1178, 78, center+dz, 'mcwlights:bell_wall_lantern', reason='warm small wall-bracket lantern', facing='west')
    for x, dz in ((1180, -4), (1185, -4), (1179, -3), (1179, 3)):
        for y in (71, 72):
            p.put(x, y, center+dz, 'minecraft:chiseled_stone_bricks' if y == 71 else 'chipped:small_andesite_bricks', reason='dressed tapered corner foot')
        for y in (75, 76):
            p.put(x, y, center+dz, 'mythrais:spiral_column_stone', reason='narrow carved upper corner instead of a continuous heavy post', facing='north', colour=1)


def ceiling_depth(p, center):
    # These ribs sit immediately below real existing floors/roof supports. The
    # western lower field stops before the stair opening; its longitudinal
    # trimmer ties back into the front wall, not an unsupported end in mid-air.
    for dz in (-2, 0):
        for x in range(1180, 1183):
            p.put(x, 75, center+dz, 'dawnoftimebuilder:dark_oak_support_beam', reason='supported lower control-room coffer rib',
                  axis='x', pillar_connection='nothing', subaxis=False, waterlogged=False)
    for dz in range(-3, 1):
        p.put(1183, 75, center+dz, 'dawnoftimebuilder:spruce_support_beam', reason='longitudinal trimmer around the protected stair opening',
              axis='z', pillar_connection='nothing', subaxis=False, waterlogged=False)
    for dz in (-2, 2):
        for x in range(1180, 1186):
            p.put(x, 81, center+dz, 'dawnoftimebuilder:dark_oak_support_beam', reason='wall-to-wall upper gallery roof rib',
                  axis='x', pillar_connection='nothing', subaxis=False, waterlogged=False)


def bank_depth(p):
    # Recess existing solid upper bank faces only. These normal stair shapes
    # remove opaque volume; no new solid is added to water or the river channel.
    for x, y, z in sorted(p.bank_mask):
        p.stair(x, y, z, 'minecraft:stone_brick_stairs', 'west', half='bottom' if y == 65 else 'top',
                reason='recessed chamfered spandrel in an existing authored dry bank face')


def construct(registry, full):
    p = Towers(registry, full)
    for center in CENTERS:
        for x in range(1178, 1188):
            for z in range(center-5, center+6):
                for y in range(82, 97):
                    p.put(x, y, z, AIR, reason='retire old broad roof cap and reserve the new fixed roof envelope')
        for inset in range(4): roof_course(p, center, inset, half_hip=center == CENTERS[1])
        window_bays(p, center)
        ceiling_depth(p, center)
        if center == CENTERS[0]: north_lantern(p, center)
        else: south_gables_and_bell(p, center)
    bank_depth(p)
    validate(p)
    return p


def validate(p):
    if any(p.blocks.get(pos, AIR) != p.original.get(pos, AIR) for pos in p.protected):
        raise UserError('Existing native machinery, stairs, headroom or BE changed')
    changed = {pos: state for pos, state in p.blocks.items() if state != p.original.get(pos, AIR)}
    if not changed or len(changed) > 3500: raise UserError('Bounded fixed-tower revision expected')
    if any(leaf_name(pos) for pos in changed): raise UserError('No moving geometry authority')
    if any(pos[0] >= 1187 and state != AIR and pos not in p.bank_mask for pos, state in changed.items()):
        raise UserError('New solids must remain west of the leaf/sweep corridor')
    checks = [require_material_rule({pos: state for pos, state in p.blocks.items()
                                    if 1178 <= pos[0] <= 1187 and 70 <= pos[1] <= 96 and abs(pos[2]-center) <= 5},
                                   'complete '+('north lantern' if center == CENTERS[0] else 'south bell')+' tower') for center in CENTERS]
    checks.append(require_outdoor_rule(p.blocks, 'entire authored bridge including fixed revision'))
    return {'changed': changed, 'material_checks': checks, 'bank_recess_cells': len(p.bank_mask),
            'new_default_bell_BE': [1178, 79, CENTERS[1]+2],
            'existing_BE_payloads_unchanged': True, 'new_glue_or_mechanical_changes': False}


def author(home, full_base, output):
    """Write geometry for review only; no native admission or current-save plan."""
    home, full_base, output = (Path(value).resolve() for value in (home, full_base, output))
    if output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('New owned private geometry proposal directory required')
    reserve = guard(2*MIB, MAX_OUTPUT)
    if digest(full_base) != BASE_SHA: raise UserError('Exact corrected future full physical base required')
    registry = read_json(home/'dashboard/settlement/registry.json'); full = read_json(full_base)
    p = construct(registry, full); proof = validate(p)
    geometry = {'format': 'awft-fixed-tower-geometry:1', 'base_physical_sha256': BASE_SHA,
                'changes': [[*pos, state] for pos, state in sorted(proof['changed'].items())],
                'authority': 'ARTWORK ONLY - no current native preimage, placement or commissioning authority'}
    palette = sorted(set(p.blocks.values())); indices = {value: i for i, value in enumerate(palette)}
    future = copy.deepcopy(full)
    future.update(palette=palette, blocks=[[*pos, indices[state]] for pos, state in sorted(p.blocks.items())], verification_only=True)
    docs = {'geometry.json': geometry, 'future-full-verification-UNBOUND.json': future}
    raw = {name: encoded(doc) for name, doc in docs.items()}
    receipt = {'format': 'awft-fixed-tower-artwork-proposal:1', 'base_physical_sha256': BASE_SHA,
               'changed_fixed_positions': len(proof['changed']), 'material_checks': proof['material_checks'],
               'existing_BE_payloads_unchanged': True, 'new_default_bell_BE': proof['new_default_bell_BE'],
               'known_solid_bank_recess_cells': proof['bank_recess_cells'],
               'moving_geometry_or_programs_changed': False, 'native_actions': False, 'reserve_guard': reserve,
               'source_sha256': digest(Path(__file__)), 'comparison_cameras': CAMERAS,
               'model_scope': 'Pinned native Mythrais lower+upper67 roof parts, actual Macaw joined windows, Dawn ceiling ribs/vanilla supports and small bracket lights; native view/model/collision checks pending',
               'next_gate': 'Fresh stopped post-moving-cycle checkpoint, exact saved/current physical preimage and parent-reviewed fixed-only admission; no generic plan emitted',
               'files': {name: {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()} for name, value in raw.items()}}
    raw['manifest.json'] = encoded(receipt)
    if sum(map(len, raw.values())) > MAX_OUTPUT: raise UserError('Artwork allocation bound exceeded')
    output.mkdir(parents=True, exist_ok=False)
    for name, value in raw.items(): (output/name).write_bytes(value)
    return dict(receipt, output=str(output))


def prepare(home, artwork, full_base, output, checkpoint_id, checkpoint_sha):
    """Fresh saved-state admission inputs only; never invokes a native action."""
    home, artwork, full_base, output = (Path(value).resolve() for value in (home, artwork, full_base, output))
    if (output.exists() or not output.is_relative_to(home/'staging')
            or not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))):
        raise UserError('New private artistic-world binding directory required')
    reserve = guard(2*MIB, MAX_OUTPUT)
    if (digest(artwork/'geometry.json') != GEOMETRY_SHA
            or digest(artwork/'future-full-verification-UNBOUND.json') != FUTURE_SHA
            or digest(full_base) != BASE_SHA):
        raise UserError('Exact frozen separate tower artwork and physical base required')
    checkpoint = read_json(home/'dashboard/settlement/backup-receipt.json')
    if (checkpoint.get('verified') is not True or checkpoint.get('id') != checkpoint_id
            or checkpoint.get('sha256') != checkpoint_sha):
        raise UserError('Exact current verified stopped checkpoint required')
    registry = read_json(home/'dashboard/settlement/registry.json'); master = read_json(full_base)
    if master['world_path'] != registry['world_path'] or master['seed'] != registry['seed']:
        raise UserError('Artwork belongs to another world')
    p = construct(registry, master); proof = validate(p); changed = proof['changed']
    if [[*pos, state] for pos, state in sorted(changed.items())] != read_json(artwork/'geometry.json')['changes']:
        raise UserError('Pure source geometry drifted from the frozen artwork')
    snapshot = BackupWorld(home, checkpoint, registry)
    try:
        # Every supplied native property remains strict. Unspecified defaults
        # are measured in the exact before plan, never inferred from the source.
        for pos, expected in p.original.items():
            actual = snapshot.state(pos)
            if base(actual) != base(expected) or any(properties(actual).get(k) != v for k, v in properties(expected).items()):
                raise UserError('Saved complete bridge base differs at '+str(pos)+'; preserve the checkpoint and native closure proof')
        before = {pos: snapshot.state(pos) for pos in changed}
        if any(pos in snapshot.protected for pos in changed):
            raise UserError('A tower target is an actual saved BE, including default/unwritten content')
        for pos, actual in before.items():
            if pos not in p.original and base(actual) not in ('minecraft:air', 'minecraft:cave_air'):
                raise UserError('Preserve unrelated saved solid at a new roof/bay target: '+str(pos))
        sources = list(snapshot.sources)
    finally: snapshot.close()
    full = read_json(artwork/'future-full-verification-UNBOUND.json')
    full['backup_sha256'] = checkpoint_sha
    documents = {'before.json': payload(master, before, checkpoint_sha, 'VERIFY ONLY - exact current fixed tower preimage'),
                 'fixed-tower-delta.json': payload(master, changed, checkpoint_sha, 'Lanternwater fixed tower depth delta ONLY'),
                 'full-verification.json': full,
                 'rollback.json': payload(master, before, checkpoint_sha, 'RECOVERY ONLY - reviewed exact fixed tower before states')}
    documents['fixed-tower-delta.json'].update(block_entities=[], commands=[], landmarks=[])
    raw = {name: encoded(value) for name, value in documents.items()}
    manifest = {'format': 'awft-fixed-tower-current-admission:1', 'source_sha256': digest(Path(__file__)),
                'frozen_geometry_sha256': GEOMETRY_SHA, 'future_physical_base_sha256': BASE_SHA,
                'checkpoint_id': checkpoint_id, 'checkpoint_sha256': checkpoint_sha,
                'exact_saved_base_positions_checked': len(p.original), 'changed_fixed_positions': len(changed),
                'current_actual_BEs_targeted_or_replayed': 0, 'new_default_bell_BE': proof['new_default_bell_BE'],
                'moving_geometry_controls_programs_unchanged': True, 'material_checks': proof['material_checks'],
                'saved_sources': sources, 'native_actions': False, 'reserve_guard': reserve,
                'comparison_cameras': CAMERAS,
                'gate': 'Fresh native before776 zero differences, placement of ONLY fixed-tower-delta, complete native full verification; then match actual views/walking/model clearance and rebind future mechanical evidence to the new full SHA',
                'files': {name: {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()} for name, value in raw.items()}}
    raw['manifest.json'] = encoded(manifest)
    if sum(map(len, raw.values())) > MAX_OUTPUT: raise UserError('Tower binding exceeded its finite allocation')
    output.mkdir(parents=True, exist_ok=False)
    for name, value in raw.items(): (output/name).write_bytes(value)
    return dict(manifest, output=str(output))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('home', 'full-base', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    print(json.dumps(author(**vars(parser.parse_args())), indent=2))
