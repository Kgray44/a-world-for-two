import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tests.test_artistic_engineering import registry as quarter_registry
from tests.test_settlement_attractions import SurfaceWorld
from tools.artistic_engineering import construct as quarter, payload as quarter_payload
from tools.artistic_mill_detail import (AIR, JOIN_APIS, PLACED_R3_SHA, Finish, construct,
    corrected_placed_states, decode, joined_dormer_top_part, joined_window_part,
    payload, validate, verify_saved_joined_states)
from tools.settlement_attractions import base, properties


def registry():
    """Synthetic world identity; additional schemas match native block exports."""
    r = quarter_registry()
    cardinal = ['north', 'south', 'west', 'east']
    boolean = ['true', 'false']
    for wood in ('oak', 'spruce'):
        r['blocks']['handcrafted:'+wood+'_shelf'] = {
            'facing': cardinal, 'shape': ['single', 'left', 'middle', 'right'],
            'type': list(map(str, range(1, 6)))}
    r['blocks']['handcrafted:terracotta_bowl'] = {
        'facing': cardinal, 'pieces': list(map(str, range(1, 7))), 'waterlogged': boolean}
    r['blocks']['mcwlights:iron_chandelier'] = {'lit': boolean}
    r['blocks']['mcwlights:tavern_wall_lantern'] = {'facing': cardinal}
    r['blocks']['mcwroofs:dark_prismarine_roof'] = {
        'facing': cardinal, 'half': ['top', 'bottom'],
        'shape': ['straight', 'inner_left', 'inner_right', 'outer_left', 'outer_right']}
    r['blocks']['mcwwindows:dark_oak_log_parapet'] = {'facing': cardinal, 'part': ['flower', 'empty']}
    for wood in ('dark_oak', 'spruce'):
        r['blocks']['mcwwindows:'+wood+'_louvered_shutter'] = {
            'facing': cardinal, 'hinge': ['left', 'right'], 'open': boolean}
        r['blocks']['mcwwindows:'+wood+'_plank_window'] = {
            'facing': ['north', 'east'], 'part': [
                'base', 'top', 'middle', 'bottom', 'top_l', 'top_m', 'top_r',
                'mid_l', 'mid_m', 'mid_r', 'bot_l', 'bot_m', 'bot_r',
                'single_l', 'single_m', 'single_r']}
    for wood in ('birch', 'oak', 'spruce'):
        r['blocks']['minecraft:'+wood+'_wood'] = {'axis': ['x', 'y', 'z']}
    for material in ('dark_prismarine', 'polished_blackstone', 'smooth_sandstone'):
        r['blocks']['minecraft:'+material] = {}
    r['blocks']['minecraft:dark_oak_trapdoor'] = {
        'facing': cardinal, 'half': ['top', 'bottom'], 'open': boolean,
        'powered': boolean, 'waterlogged': boolean}
    return r


class Saved:
    def __init__(self, original):
        self.original, self.override, self.protected = original, {}, set()

    def state(self, pos):
        return self.override.get(pos, self.original.get(pos, AIR if pos[1] >= 67 else 'minecraft:stone'))


class MillFinishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = registry()
        q = quarter(cls.registry, SurfaceWorld())
        cls.source = quarter_payload(q, q.blocks, 'a'*64, 'SYNTHETIC TEST ONLY', include_tags=True)
        cls.manifest = {'systems': q.systems, 'routes': q.routes}
        cls.finish = construct(cls.registry, cls.source, cls.manifest)

    def changed(self):
        p = copy.copy(self.finish)
        p.blocks, p.previous, p.tags = p.blocks.copy(), p.previous.copy(), p.tags.copy()
        return p

    def test_hydraulic_seal_machine_moat_cargo_lids_and_routes_remain_fixed(self):
        p = self.finish
        for local in ((-5, 2, 0), (-1, 3, 0), (0, 3, 0), (5, 8, 0), (7, 1, 4), (1, 2, 11)):
            with self.subTest(local=local), self.assertRaisesRegex(UserError, 'Preserve'):
                p.put(*local, 'minecraft:stone')
        self.assertFalse(set(p.blocks) & p.fixed)
        self.assertFalse(set(p.blocks) & {tuple(v) for v in self.manifest['systems']['hypertube']['native_collision_cells']})

    def test_exact_saved_architecture_fluids_and_foreign_block_entities_refuse(self):
        original = self.finish.original
        for old in ('minecraft:water[level=0]', 'minecraft:chest', 'minecraft:oak_leaves'):
            saved = Saved(original)
            saved.override[self.finish.world(-7, 4, -2)] = old
            p = Finish(self.registry, self.source, self.manifest, saved)
            with self.assertRaisesRegex(UserError, 'Preserve'):
                p.put(-7, 4, -2, 'mcwlights:tavern_wall_lantern', facing='west')
        saved = Saved(original)
        pos = self.finish.world(5, 2, -6)
        saved.protected.add(pos)
        p = Finish(self.registry, self.source, self.manifest, saved)
        with self.assertRaisesRegex(UserError, 'saved block entity'):
            p.put(5, 2, -6, 'minecraft:stone')
        saved.protected.clear()
        saved.override[pos] = 'minecraft:gold_block'
        with self.assertRaisesRegex(UserError, 'predecessor changed'):
            p.put(5, 2, -6, 'minecraft:stone')

    def test_ridge_is_joined_and_articulation_meets_composed_material_rules(self):
        self.assertFalse(validate(self.finish)['building_material_rule']['violations'])
        self.assertFalse(validate(self.finish)['outdoor_nine_rule']['violations'])
        p = self.changed()
        p.blocks[p.world(6, 12, 0)] = AIR
        with self.assertRaisesRegex(UserError, 'daylight gap'):
            validate(p)
        p = self.changed()
        p.blocks[p.world(0, 11, -4)] = AIR
        with self.assertRaisesRegex(UserError, 'dormer gable'):
            validate(p)
        p = self.changed()
        for x in range(4):
            for z in range(4):
                p.blocks[p.world(x, 16, z)] = 'minecraft:birch_wood[axis='+('x' if x % 2 else 'z')+']'
        with self.assertRaisesRegex(ValueError, 'material run rule'):
            validate(p)

    def test_real_modded_window_assemblies_and_preserved_technical_inspection(self):
        p = self.finish
        self.assertIn('mcwwindows:dark_oak_plank_window', p.blocks[p.world(9, 2, 10)])
        self.assertIn('part=base', p.blocks[p.world(0, 8, 6)])
        self.assertIn('part=top', p.blocks[p.world(0, 9, 6)])
        for local in ((-5, 2, 0), (1, 2, -6), (0, 3, -4)):
            self.assertNotIn(p.world(*local), p.blocks)
        p = self.changed()
        p.blocks[p.world(9, 2, 10)] = 'minecraft:glass'
        with self.assertRaisesRegex(UserError, 'fancy window'):
            validate(p)

    def test_proposal_keeps_exact_preimage_and_has_no_runtime_commands(self):
        p = self.finish
        self.assertEqual(set(p.previous), set(p.blocks))
        self.assertLess(len(p.blocks), 1000)
        native = payload(p, p.blocks, 'a'*64, 'synthetic finish', True)
        self.assertEqual(native['commands'], [])
        self.assertIn('STAGED', native['validation'])
        self.assertEqual(len(native['block_entities']), 1)
        self.assertEqual(p.original[p.world(7, 1, 4)], AIR)


class NativeMacawJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=registry()
        quarter_plan=quarter(cls.registry,SurfaceWorld())
        cls.r2=quarter_payload(quarter_plan,quarter_plan.blocks,'a'*64,'SYNTHETIC R2',include_tags=True)
        cls.finish=construct(cls.registry,cls.r2,{'systems':quarter_plan.systems,'routes':quarter_plan.routes})
        cls.fixture=json.loads((Path(__file__).parent/'fixtures/mill_native_joined_parts.json').read_text('utf-8'))

    def prior_plan(self):
        plan=payload(self.finish,self.finish.blocks,'b'*64,'Synthetic captured prior R3',True)
        by_position={tuple(row[:3]):row for row in plan['blocks']}
        for observed in self.fixture['observations']:
            value=observed['original_state']
            if value not in plan['palette']:plan['palette'].append(value)
            by_position[tuple(observed['position'])][3]=plan['palette'].index(value)
        return plan

    def test_native_82_position_fixture_matches_corrected_canonical_builder(self):
        self.assertEqual(self.fixture['native_apis'],JOIN_APIS)
        self.assertEqual(self.fixture['original_placed_plan_sha256'],PLACED_R3_SHA)
        self.assertEqual(len(self.fixture['observations']),82)
        for observed in self.fixture['observations']:
            pos=tuple(observed['position']);expected=self.finish.blocks[pos]
            self.assertEqual(base(expected),base(observed['native_state']))
            actual_fields=properties(observed['native_state'])
            for key,value in properties(expected).items():
                self.assertEqual(actual_fields.get(key),value,(pos,key))

    def test_pinned_window_edge_and_ridge_neighbor_rules_match_native_witnesses(self):
        for observed in self.fixture['observations']:
            actual=properties(observed['native_state']);neighbors=observed['same_block_neighbors']
            if base(observed['native_state']).startswith('mcwwindows:'):
                negative,positive=('west','east') if actual['facing']=='north' else ('north','south')
                # A single-column initial part is deliberately outside this
                # correction. It remains exactly as captured, not normalized.
                if neighbors[negative] or neighbors[positive]:
                    self.assertEqual(joined_window_part(neighbors['above'],neighbors['below'],
                        neighbors[negative],neighbors[positive]),actual['part'])
            else:
                self.assertEqual(joined_dormer_top_part(neighbors['east'],neighbors['west'],
                    north=neighbors['north'],south=neighbors['south']),actual['part'])
        with self.assertRaises(UserError):joined_dormer_top_part(True,True,north=True)
        with self.assertRaises(UserError):joined_window_part(1,False,False,True)

    def test_exactly_63_part_changes_preserve_every_position_identity_facing_and_tag(self):
        prior=self.prior_plan();preserved=copy.deepcopy(prior)
        corrected,changes=corrected_placed_states(self.registry,prior,self.r2)
        self.assertEqual(prior,preserved)
        self.assertEqual(len(changes),63)
        self.assertEqual(sum(base(x['before']).startswith('mcwwindows:') for x in changes),54)
        self.assertEqual(sum(base(x['before'])=='mcwroofs:spruce_top_roof' for x in changes),9)
        self.assertEqual(set(decode(prior)),set(decode(corrected)))
        self.assertEqual(prior['block_entities'],corrected['block_entities'])
        self.assertEqual(prior['commands'],corrected['commands'])
        for changed in changes:
            before,after=changed['before'],changed['after']
            self.assertEqual(base(before),base(after))
            first,last=properties(before),properties(after)
            self.assertEqual({k:v for k,v in first.items() if k!='part'},
                             {k:v for k,v in last.items() if k!='part'})
        # This observed vertical-only base was not one of the native failures.
        self.assertEqual(decode(corrected)[1310,75,-994],decode(prior)[1310,75,-994])

    def test_saved_verification_refuses_any_other_identity_facing_or_part_mismatch(self):
        corrected,_=corrected_placed_states(self.registry,self.prior_plan(),self.r2)
        actual=decode(corrected)
        window=next(p for p,v in actual.items() if v.startswith('mcwwindows:') and properties(v).get('part')=='bot_r')
        for replacement in ('minecraft:stone',actual[window].replace('facing=north','facing=east')
                            .replace('facing=east','facing=south'),actual[window].replace('part=bot_r','part=bot_l')):
            saved=Saved(actual);saved.override[window]=replacement
            with self.assertRaises(UserError):verify_saved_joined_states(corrected,saved)
        # Native default fields already omitted from the authored request are
        # not newly invented expectations. Every supplied property still holds.
        saved=Saved(actual)
        cup=next(p for p,v in actual.items() if base(v)=='handcrafted:wood_cup')
        fields=properties(actual[cup]);fields.update(pieces='1',waterlogged='false')
        saved.override[cup]=base(actual[cup])+'['+','.join(k+'='+v for k,v in sorted(fields.items()))+']'
        verify_saved_joined_states(corrected,saved)


if __name__ == '__main__':
    unittest.main()
