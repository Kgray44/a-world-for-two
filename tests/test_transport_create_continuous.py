"""Fixed basin closure, inventory custody and independent dry/wet source checks."""
import json
import unittest

from control_room.common import UserError
from tests.test_transport_create_shops import SCHEMAS
from tools import transport_create_continuous as motor


def fixture():
    registry = {'seed': 7, 'world_path': 'D:/test/world', 'blocks': {
        **SCHEMAS, 'minecraft:glass': {},
        'minecraft:mangrove_slab': {'type': ['top', 'bottom', 'double'], 'waterlogged': ['false', 'true']},
        'create:water_wheel': {'facing': ['north', 'south', 'east', 'west', 'up', 'down']},
        'create:gearbox': {'axis': ['x', 'y', 'z']},
        'create:clutch': {'axis': ['x', 'y', 'z'], 'powered': ['false', 'true']},
        'minecraft:lever': {'face': ['floor', 'wall', 'ceiling'], 'facing': ['north', 'south', 'east', 'west'], 'powered': ['false', 'true']},
        'minecraft:hopper': {'facing': ['down', 'north', 'south', 'east', 'west'], 'enabled': ['false', 'true']},
        'minecraft:water': {'level': [str(i) for i in range(16)]},
    }}
    dry = motor.layout(registry)
    positions = set(dry) | set(motor.INTERIOR) | set(motor.BASE_CAP)
    positions |= {(x, y+dy, z) for x, y, z in motor.STANDS for dy in (0, 1)}
    floor = {(x, 64, z) for x, _, z in set(dry) | set(motor.STANDS)}
    full = {q: motor.AIR for q in positions}
    full.update({q: motor.SEAL_PLANK for q in floor | set(motor.BASE_CAP)})
    full.update({q: motor.TOP for q in motor.SLABS})
    source = {'origin': [0, 0, 0], 'routes': [{'feet_local': [list(motor.STANDS[0])]}], 'rooms': [],
              'complete_expected_state_context_ONLY': [[*q, s] for q, s in full.items()]}
    _, _, _, _, context = motor.geometry(registry, source)
    actual = {q: full.get(q, motor.AIR) for q in set(dry) | context}
    return registry, source, actual


class ContinuousShopTests(unittest.TestCase):
    def setUp(self):
        self.registry, self.source, self.actual = fixture()

    def derive(self, actual=None, protected=()):
        return motor.derive(self.registry, self.source, self.actual if actual is None else actual, protected, 'a'*64)

    def test_every_wet_cell_has_all_six_faces_inside_or_in_literal_seal(self):
        boundary = motor.SIDES | motor.ENDS | motor.BASE_CAP
        self.assertEqual(len(motor.INTERIOR), 9)
        for x, y, z in motor.INTERIOR:
            for dx, dy, dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                self.assertIn((x+dx, y+dy, z+dz), motor.INTERIOR | boundary)
        self.assertNotIn(motor.WATER, motor.SLABS)
        self.assertNotIn(motor.WHEEL, boundary)

    def test_wet_activation_is_one_source_and_never_replays_dry_hardware(self):
        docs = self.derive()
        wet = json.loads(docs['one-water-source-PROPOSAL.json'])
        self.assertEqual(wet['blocks'], [[*motor.WATER, 0]])
        self.assertEqual(wet['palette'], ['minecraft:water[level=0]'])
        dry = json.loads(docs['dry-hardware-PROPOSAL.json'])
        self.assertEqual(len(dry['blocks']), 33)
        self.assertNotIn('minecraft:water[level=0]', dry['palette'])
        for name, raw in docs.items():
            v = json.loads(raw)
            self.assertEqual(v['commands'], [])
            self.assertEqual(v['block_entities'], [])
            self.assertEqual(v['construction_forbidden'], not name.endswith('PROPOSAL.json'))

    def test_only_two_precise_top_slabs_gain_bottom_half(self):
        dry = motor.layout(self.registry)
        self.assertEqual({q for q in dry if self.actual[q] != motor.AIR}, motor.SLABS)
        self.assertTrue(all(dry[q] == motor.DOUBLE for q in motor.SLABS))
        for wrong in ('minecraft:air', 'minecraft:mangrove_slab[type=bottom,waterlogged=false]',
                      'minecraft:mangrove_slab[type=top,waterlogged=true]'):
            changed = dict(self.actual)
            changed[next(iter(motor.SLABS))] = wrong
            with self.assertRaises(UserError):
                self.derive(changed)

    def test_saved_furniture_block_entities_and_changed_floor_are_preserved(self):
        for q in (motor.WHEEL, next(iter(motor.SIDES)), next(iter(motor.BASE_CAP))):
            changed = dict(self.actual)
            changed[q] = 'minecraft:barrel[facing=up,open=false]'
            with self.assertRaises(UserError):
                self.derive(changed)
        with self.assertRaises(UserError):
            self.derive(protected=[motor.WHEEL])

    def test_gearbox_axes_side_cog_and_separate_real_stop_controls_are_explicit(self):
        dry = motor.layout(self.registry)
        self.assertEqual(dry[1328, 66, -1203], 'create:gearbox[axis=y]')
        self.assertEqual(dry[1326, 66, -1203], 'create:gearbox[axis=z]')
        self.assertEqual(dry[1326, 65, -1203], 'create:cogwheel[axis=y,waterlogged=false]')
        self.assertEqual(dry[motor.HOPPER], 'minecraft:hopper[enabled=false,facing=down]')
        self.assertEqual(dry[motor.CLUTCH], 'create:clutch[axis=x,powered=true]')
        self.assertEqual(motor.INPUT, (motor.MILL[0], motor.MILL[1]+2, motor.MILL[2]))
        self.assertEqual(motor.DRIVE_LEVER, (motor.CLUTCH[0], motor.CLUTCH[1], motor.CLUTCH[2]+1))

    def test_blocked_service_body_and_missing_saved_cell_refuse(self):
        for q in motor.STANDS + (next(iter(motor.INTERIOR)),):
            changed = dict(self.actual)
            changed[q] = 'minecraft:stone'
            with self.assertRaises(UserError):
                self.derive(changed)
        missing = dict(self.actual)
        missing.pop(next(iter(missing)))
        with self.assertRaises(UserError):
            self.derive(missing)


if __name__ == '__main__':
    unittest.main()
