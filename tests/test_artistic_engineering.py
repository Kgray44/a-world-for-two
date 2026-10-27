import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from control_room.common import UserError
from tests.test_settlement_attractions import fixture as machine_registry, SurfaceWorld
from tools.artistic_engineering import (
    AIR, Quarter, SPANS, checked_after_plan, checked_native_proof,
    checked_proof_order, construct, payload, validate, walk_columns,
)


def registry():
    """Synthetic identity, with block schemas selected from actual native exports."""
    result = machine_registry().registry
    source = Path(__file__).parent/'fixtures/artistic_street_registry.json'
    street = json.loads(source.read_text(encoding='utf-8'))
    result['blocks'].update(street['blocks'])
    result['items'] = sorted(set(result['items']) | set(street['items']))
    cardinal = ['north', 'south', 'west', 'east']
    roof = {'facing': cardinal, 'half': ['top', 'bottom'],
            'shape': ['straight', 'inner_left', 'inner_right', 'outer_left', 'outer_right']}
    for key in ('mcwroofs:dark_oak_planks_roof', 'mcwroofs:spruce_planks_roof'):
        result['blocks'][key] = roof
    for key in ('minecraft:mud_bricks', 'minecraft:flowering_azalea'):
        result['blocks'][key] = {}
    for key in ('minecraft:oak_log', 'minecraft:spruce_log'):
        result['blocks'][key] = {'axis': ['x', 'y', 'z']}
    result['blocks']['minecraft:composter'] = {'level': list(map(str, range(9)))}
    result['blocks']['minecraft:dark_oak_fence'] = {
        **{k: ['true', 'false'] for k in cardinal}, 'waterlogged': ['true', 'false']}
    result['blocks']['minecraft:grindstone'] = {'face': ['floor', 'wall', 'ceiling'], 'facing': cardinal}
    result['blocks']['supplementaries:sack'] = {'open': ['true', 'false'], 'waterlogged': ['true', 'false']}
    result['blocks']['railways:track_dark_oak'] = result['blocks']['railways:track_spruce'].copy()
    return result


class ArtisticEngineeringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = registry()
        cls.plan = construct(cls.reg, SurfaceWorld())

    def changed(self):
        plan = copy.copy(self.plan)
        plan.blocks = self.plan.blocks.copy()
        plan.tags = self.plan.tags.copy()
        plan.systems = copy.deepcopy(self.plan.systems)
        return plan

    def test_real_complementary_systems_and_bounded_walkable_quarter(self):
        p = self.plan
        check = validate(p)
        self.assertEqual(check['track_blocks'], 62)
        self.assertEqual(check['native_tube_spans'], 6)
        self.assertEqual(p.systems['railway']['station_distance_blocks'], 52)
        self.assertEqual(p.systems['hypertube']['native_span_lengths'], [8]*6)
        self.assertEqual(SPANS[0], (9, 17))
        self.assertEqual(SPANS[-1], (49, 57))
        self.assertEqual(len(p.systems['railway']['bogeys']), 2)
        self.assertEqual(p.systems['railway']['seats'], 3)
        self.assertTrue(all(not row['violations'] for row in check['material_rule']))
        self.assertFalse(check['outdoor_nine_rule']['violations'])
        self.assertGreater(len(p.routes), 7)
        self.assertGreater(len(p.rooms), 2)

    def test_water_outlet_and_any_open_containment_face_fail(self):
        for local in ((-5, 2, 0), (-1, 3, 0), (-3, 0, 1)):
            plan = self.changed()
            plan.blocks[plan.world(local)] = AIR
            with self.assertRaisesRegex(UserError, 'containment|component'):
                validate(plan)

    def test_real_drive_connections_pump_route_and_actual_filter_are_required(self):
        for local in ((14, 3, 0), (19, 2, 0), (20, 2, 36), (21, 3, 57), (1, 3, -7)):
            plan = self.changed()
            plan.blocks[plan.world(local)] = AIR
            with self.assertRaises(UserError):
                validate(plan)
        plan = self.changed()
        plan.tags[plan.world((4, 4, 0))] = '{}'
        with self.assertRaisesRegex(UserError, 'filter'):
            validate(plan)

    def test_native_curve_envelope_cannot_replace_saved_obstacle_or_forge_links(self):
        plan = self.changed()
        cell = tuple(plan.systems['hypertube']['native_collision_cells'][10])
        plan.blocks[cell] = 'minecraft:stone'
        with self.assertRaisesRegex(UserError, 'collision cells'):
            validate(plan)
        self.assertTrue(all(b-a <= 40 for a, b in SPANS))
        self.assertEqual(self.plan.systems['hypertube']['run_state'].split(';')[0], 'Not connected')

    def test_railway_glue_does_not_capture_track_platform_or_tube(self):
        plan = self.changed()
        plan.systems['railway']['carriage_glue_min'][1] -= 1
        with self.assertRaisesRegex(UserError, 'glue custody'):
            validate(plan)
        for z in (8, 14):
            plan = self.changed()
            plan.blocks[plan.world((26, 3, z))] = 'create:small_bogey[axis=x]'
            with self.assertRaises(UserError):
                validate(plan)

    def test_blocked_egress_or_operating_aisle_cannot_pass_later_validation(self):
        for local in ((21, 4, 7), (24, 4, 60), (7, 1, 4)):
            plan = self.changed()
            plan.blocks[plan.world(local)] = 'minecraft:stone'
            with self.assertRaisesRegex(UserError, 'route'):
                validate(plan)

    def test_saved_trees_fluids_inventory_and_authored_air_are_fixed(self):
        position = self.plan.world((1, 1, 1))
        for saved in ('minecraft:oak_leaves', 'minecraft:water[level=0]', 'minecraft:chest'):
            world = SurfaceWorld()
            world.override[position] = saved
            plan = Quarter(self.reg, world)
            with self.assertRaisesRegex(UserError, 'Preserve'):
                plan.put(1, 1, 1, AIR)
        world = SurfaceWorld()
        world.protected.add(position)
        with self.assertRaises(UserError):
            Quarter(self.reg, world).put(1, 1, 1, AIR)
        exclusion = {'world_path': self.reg['world_path'], 'seed': self.reg['seed'], 'blocks': [[*position, 0]]}
        with self.assertRaisesRegex(UserError, 'reserved air'):
            Quarter(self.reg, SurfaceWorld(), [('existing', exclusion, 'a'*64)]).put(1, 1, 1, AIR)

    def test_natural_shrub_detour_and_no_fabricated_execution(self):
        self.assertNotIn(16, walk_columns(44))
        self.assertEqual(tuple(walk_columns(45)), (18, 19))
        native = payload(self.plan, self.plan.blocks, 'a'*64, 'synthetic only', include_tags=True)
        self.assertEqual(native['commands'], [])
        self.assertIn('STAGED ONLY', native['validation'])
        self.assertFalse(self.plan.systems['railway']['initially_assembled'])
        self.assertEqual(self.plan.systems['watermill']['initial_water'], 'dry')
        self.assertTrue(self.plan.systems['watermill']['initially_stopped'])

    def test_unequal_state_orientation_is_not_a_material_rule_escape(self):
        plan = self.changed()
        cells = plan.groups['The Copper Wren watermill']
        for x in range(6):
            for z in range(6):
                pos = plan.world((x, 13, z))
                plan.blocks[pos] = 'minecraft:oak_log[axis='+('x' if x % 2 else 'z')+']'
                cells = cells | {pos}
        plan.groups = dict(plan.groups, **{'The Copper Wren watermill': cells})
        with self.assertRaisesRegex(ValueError, 'material run rule'):
            validate(plan)


class NativeCommissioningAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'native-proof.json'
        self.now = datetime(2026, 10, 27, 15, tzinfo=timezone.utc)

    def evidence(self, age=10, **changes):
        proof = {'operation': 'verify', 'plan_sha256': 'a'*64, 'blocks': 7710,
                 'failures': 0,
                 'status': 'verified actual block identities, orientation, block entities and supplied inventories',
                 'started': (self.now-timedelta(seconds=age+2)).isoformat(),
                 'finished': (self.now-timedelta(seconds=age)).isoformat()}
        proof.update(changes)
        self.path.write_text(json.dumps(proof), encoding='utf-8')
        self.path.with_name(self.path.name+'.complete').write_text(
            hashlib.sha256(self.path.read_bytes()).hexdigest(), encoding='utf-8')
        return proof

    def check(self, **kwargs):
        return checked_native_proof(self.path, 'a'*64, 7710, now=self.now, **kwargs)

    def test_original_preimage_is_historical_current_target_must_be_fresh(self):
        self.evidence(age=3*86400)
        self.assertEqual(self.check(maximum_age=None)[0]['blocks'], 7710)
        with self.assertRaisesRegex(UserError, 'Reverify'):
            self.check()
        self.evidence(age=1200)
        self.check()
        self.evidence(age=1201)
        with self.assertRaises(UserError):
            self.check()

    def test_future_unordered_or_timezone_free_proof_never_becomes_history(self):
        for changes in ({'finished': (self.now+timedelta(seconds=1)).isoformat()},
                        {'started': self.now.isoformat()},
                        {'finished': '2026-10-27T14:59:50'}):
            with self.subTest(changes=changes):
                self.evidence(**changes)
                with self.assertRaises(UserError):
                    self.check(maximum_age=None)

    def test_native_terminal_identity_completion_and_zero_failures_are_required(self):
        for changes in ({'plan_sha256': 'b'*64}, {'blocks': 7709},
                        {'operation': 'place'}, {'failures': 1}, {'error': 'refused'}):
            self.evidence(**changes)
            with self.assertRaises(UserError):
                self.check(maximum_age=None)
        self.evidence()
        self.path.write_text(self.path.read_text()+' ', encoding='utf-8')
        with self.assertRaisesRegex(UserError, 'completion marker'):
            self.check()

    def test_only_checkpoint_reference_can_change_in_fresh_verification_plan(self):
        original = {'backup_sha256': 'a'*64, 'world_path': 'synthetic',
                    'palette': ['minecraft:air'], 'blocks': [[1, 2, 3, 0]],
                    'commands': [], 'block_entities': {}}
        backup = {'verified': True, 'sha256': 'b'*64}
        after = dict(original, backup_sha256='b'*64)
        checked_after_plan(original, after, backup)
        self.assertEqual(original['backup_sha256'], 'a'*64)
        for changed in (dict(after, blocks=[[1, 2, 4, 0]]),
                        dict(after, commands=['anything']), dict(after, world_path='other'),
                        dict(after, extra=True), original):
            with self.assertRaisesRegex(UserError, 'only the backup SHA'):
                checked_after_plan(original, changed, backup)
        with self.assertRaises(UserError):
            checked_after_plan(original, after, dict(backup, verified=False))

    def test_measurement_order_compares_instants_not_lexical_timezone_strings(self):
        before = {'started': '2026-10-27T14:00:00+02:00', 'finished': '2026-10-27T14:00:10+02:00'}
        after = {'started': '2026-10-27T12:00:11Z', 'finished': '2026-10-27T12:00:12Z'}
        checked_proof_order(before, after)
        with self.assertRaisesRegex(UserError, 'predates'):
            checked_proof_order(after, before)


if __name__ == '__main__':
    unittest.main()
