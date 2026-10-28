"""Three original harbor-mouth/river vessels, with no runtime or world actions.

These are static authored structures. Actual Small Ships/vanilla sailing and
rowing entities have their own custody and commissioning contracts.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass

from control_room.common import UserError
from tools.artistic_materials import require_material_rule
from tools.artistic_ship import AIR, SEAL_BLOCKS, interpolate
from tools.grand_harbor_fleet import FleetShip, circulation, template


SMALLCRAFT_ORDER = ('tern-pilot-cutter', 'salt-marigold-ketch', 'reed-fin-river-lighter')


@dataclass(frozen=True)
class SmallSpec:
    key: str
    name: str
    role: str
    berth: str
    stations: tuple
    keel: int
    mast_positions: tuple
    mast_heights: tuple
    cabin_front: int | None
    accent: str
    sail_state: str
    weather: int = 1

    @property
    def fore(self):
        return self.stations[0][0]

    @property
    def aft(self):
        return self.stations[-1][0]


SPECS = {
    'tern-pilot-cutter': SmallSpec(
        'tern-pilot-cutter', 'Tern', 'Single-masted pilot cutter', 'harbor-mouth-proposal',
        ((-14, .3), (-12, 1.3), (-9, 2.5), (-5, 3.5), (2, 3.7), (8, 3.1), (13, 1.8)),
        -3, (-4,), (25,), 6, 'blue', 'furled'),
    'salt-marigold-ketch': SmallSpec(
        'salt-marigold-ketch', 'Salt Marigold', 'Coastal fishing and provision ketch', 'harbor-mouth-proposal',
        ((-17, .3), (-14, 1.5), (-10, 3.0), (-5, 4.3), (4, 4.5), (11, 3.8), (16, 2.5)),
        -3, (-7, 10), (29, 20), 7, 'green', 'furled'),
    'reed-fin-river-lighter': SmallSpec(
        'reed-fin-river-lighter', 'Reed Fin', 'Shallow river cargo lighter and sculling boat', 'river-proposal',
        ((-10, .6), (-8, 2.0), (-4, 3.2), (4, 3.4), (8, 2.6), (10, 1.6)),
        -1, (), (), None, 'red', 'no-sails'),
}


class SmallCraft(FleetShip):
    def __init__(self, registry, spec):
        super().__init__(registry, spec)
        self.entry = (1, 1, 0)

    def top(self, z):
        return 3 if self.spec.cabin_front is not None else 2

    def width(self, z, y):
        s = self.spec
        if not s.fore <= z <= s.aft or not s.keel <= y <= self.top(z):
            return -1
        # A shallow flat-floored lighter and two finer round-bilged seaboats.
        sections = ((s.keel, .45), (0, 1), (3, .9)) if s.keel < -1 else ((-1, .7), (0, 1), (2, .95))
        return max(0, round(interpolate(s.stations, z)*interpolate(sections, y)))


def hull(p):
    s = p.spec
    for z in range(s.fore, s.aft+1):
        for y in range(s.keel, p.top(z)+1):
            width = p.width(z, y)
            for x in range(-width, width+1):
                shell = abs(x) == width or any(abs(x) > p.width(z+dz, y+dy)
                                              for dy, dz in ((-1, 0), (0, -1), (0, 1)))
                if shell or y == s.weather:
                    p.put(x, y, z, 'minecraft:dark_oak_planks' if y < 1 else 'minecraft:spruce_planks')
                    if shell and y <= 0:
                        p.shell_cells.add((x, y, z))
                else:
                    p.put(x, y, z, AIR)
        for side in (-1, 1):
            width = p.width(z, p.top(z))
            if width > 0:
                p.put(side*width, p.top(z)+1, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
    # Fine stem and sternpost remain visible above the shaped hull ends.
    p.spar((0, 0, s.fore), (0, 4, s.fore-2))
    p.spar((0, 0, s.aft), (0, 3, s.aft+1))


def boarding(p):
    width = p.width(0, 1)
    for z in (0, 1):
        p.box(width-1, 2, z, width, 4, z, AIR)
        p.box(width, 1, z, width+2, 1, z, 'minecraft:spruce_planks')
    # A backed return ladder reaches below the landing; it is not a boat entity.
    for y in (0, 1):
        p.put(width+2, y, 0, 'minecraft:dark_oak_log', axis='y')
        p.put(width+3, y, 0, 'minecraft:ladder', facing='east', waterlogged=y < 0)
    p.room('Boarding landing', 'boarding', (width+1, 1, 1), 'Two-wide low landing and backed return ladder; real skiff embarkation pending')
    p.room('Working deck', 'weather', (1, 1, -1), 'Clear fore-and-aft working route')
    p.fittings.append({'kind': 'boarding interface', 'local_floor': [width+1, 1, 1],
                       'quay_attachment': None, 'placement_owner': 'master'})


def cabin(p):
    s = p.spec
    if s.cabin_front is None:
        return
    front, back = s.cabin_front, s.aft-3
    for z in range(front, back+1):
        w = min(3, max(2, p.width(z, 1)))
        for side in (-1, 1):
            p.box(side*w, 2, z, side*w, 4, z, 'minecraft:dark_oak_planks')
            if front+1 <= z <= back-1:
                p.put(side*w, 3, z, 'minecraft:glass')
        p.box(-w, 5, z, w, 5, z, 'minecraft:dark_oak_slab', type='double', waterlogged=False)
    p.box(-2, 2, front, 2, 4, front, 'minecraft:spruce_planks')
    p.box(-2, 2, back, 2, 4, back, 'minecraft:spruce_planks')
    for dy, half in ((2, 'lower'), (3, 'upper')):
        p.put(1, dy, front, 'minecraft:oak_door', facing='south', half=half,
              hinge='right', open=False, powered=False)
    p.bed(-1, 1, front+1, s.accent)
    p.put(-1, 2, back-1, 'minecraft:cartography_table')
    p.put(0, 3, back-1, 'lfpirates:ship_in_bottle', facing='north', waterlogged=False)
    p.put(0, 4, front+2, 'minecraft:lantern', hanging=True, waterlogged=False)
    p.chest(-2, 2, front+3, 'Pilot charts' if len(s.mast_positions) == 1 else 'Fishing and coastal stores',
            ['minecraft:compass', 'minecraft:map', 'minecraft:bread'])
    p.room('Sheltered cabin', 'weather', (1, 1, front+2), 'Private berth, chart desk, provisions and a supported lamp')


def rig(p):
    s = p.spec
    if not s.mast_positions:
        # Stowed sweeps and stern sculling crutch identify a shallow river lighter.
        p.spar((-3, 3, -6), (-3, 3, 6), 'minecraft:stripped_spruce_log')
        p.put(-3, 4, 6, 'minecraft:oak_trapdoor', facing='south', half='bottom', open=False, powered=False, waterlogged=False)
        p.spar((0, 3, s.aft-1), (0, 5, s.aft-1))
        return
    p.spar((0, 3, s.fore+3), (0, 7, s.fore-6), 'minecraft:stripped_spruce_log')
    for index, (z, height) in enumerate(zip(s.mast_positions, s.mast_heights)):
        p.spar((0, s.keel, z), (0, height, z+1), 'minecraft:stripped_spruce_log')
        low = 8 if index == 0 else 7
        aft = min(z+9, s.aft-1)
        p.spar((0, low, z), (0, low, aft), 'minecraft:stripped_spruce_log')
        p.spar((0, height-7, z+1), (0, height-4, aft-1), 'minecraft:stripped_spruce_log')
        # Tied, furled fore-and-aft canvas stays compact at the boom.
        for zz in range(z+2, aft):
            p.put(1, low, zz, 'chipped:bundled_white_wool' if zz % 4 else 'chipped:knitted_white_wool')
        for side in (-1, 1):
            w = max(3, p.width(z, 1)+1)
            p.box(side*(w-1), 2, z, side*w, 2, z, 'minecraft:dark_oak_log', axis='x')
            p.box(side*w, 3, z, side*w, 4, z, 'minecraft:dark_oak_log', axis='y')
            p.rope((side*w, 4, z), (side, height-6, z+1))
        p.rope((0, height-2, z+1), (0, 7, s.fore-6))
        for x in (1, 2, 3):
            p.put(x, height, z+1, 'minecraft:'+s.accent+'_wool')
    p.finish_ropes()


def equipment(p):
    s = p.spec
    if not s.mast_positions:
        p.chest(-2, 2, -4, 'River provisions and boat tools', ['minecraft:bread', 'minecraft:string', 'minecraft:iron_axe'])
        for z in (3, 5):
            p.barrel(-2, 2, z)
        p.put(-1, 2, -7, 'chipped:spruce_crate', facing='up', open=False)
        p.room('River cargo and sculling station', 'weather', (1, 1, 5), 'Low cargo casks, stowed sweeps and an open stern working position')
    elif len(s.mast_positions) == 1:
        p.chest(-2, 2, 1, 'Pilot boarding and lookout kit', ['minecraft:spyglass', 'minecraft:compass', 'minecraft:string'])
        p.barrel(-2, 2, -7)
    else:
        p.barrel(-2, 2, -3)
        p.barrel(-2, 2, -1)
        p.chest(-2, 2, 3, 'Fishing lines and provisions', ['minecraft:fishing_rod', 'minecraft:string', 'minecraft:bread'])
        p.put(-3, 2, -8, 'chipped:spruce_crate', facing='up', open=False)
    p.put(-2, 2, s.fore+5, 'minecraft:dark_oak_fence')
    p.put(-2, 3, s.fore+5, 'minecraft:lantern', hanging=False, waterlogged=False)


def lower_hull_check(p):
    """Flood every authored submerged AIR cell, not merely a named room anchor."""
    s = p.spec
    half = max(abs(x) for x, _, _ in p.blocks)+2
    bounds = (-half, s.keel-1, s.fore-2, half, 0, s.aft+2)
    outside = {bounds[:3]}
    queue = deque(outside)
    shell = {pos for pos in p.shell_cells if p.local_state(*pos).split('[')[0] in SEAL_BLOCKS}
    while queue:
        pos = queue.popleft()
        for delta in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nxt = tuple(a+b for a, b in zip(pos, delta))
            if nxt in outside or nxt in shell or any(not bounds[i] <= nxt[i] <= bounds[i+3] for i in range(3)):
                continue
            outside.add(nxt)
            queue.append(nxt)
    submerged_air = {pos for pos, state in p.blocks.items() if pos[1] <= 0 and state == AIR}
    if submerged_air & outside:
        raise UserError('Source flood reaches the small-vessel interior')
    return {'method': 'Six-neighbor outside flood against protected full-block shell',
            'enclosed_submerged_air_cells': len(submerged_air), 'native_water_updates': 'UNVERIFIED'}


def build(registry, key):
    if key not in SPECS:
        raise UserError('Unknown authored small vessel: '+str(key))
    p = SmallCraft(registry, SPECS[key])
    hull(p)
    boarding(p)
    cabin(p)
    equipment(p)
    rig(p)
    checks = {'circulation': circulation(p), 'materials': require_material_rule(p.blocks, p.spec.name),
              'lower_hull_seal': lower_hull_check(p),
              'rope_attachments': getattr(p, 'rope_proof', {'positions': 0, 'reason': 'River lighter has no standing rig'}),
              'native_collision_water_and_boarding': 'UNVERIFIED'}
    design = asdict(p.spec)
    design.update(period='17th-18th century original interpretation',
                  decks=[1, 1, 1, 1], fittings=p.fittings,
                  mobility='STATIC STRUCTURE; no sailing/rowing entity or physics assembly created')
    return template(p, key, design, checks)
