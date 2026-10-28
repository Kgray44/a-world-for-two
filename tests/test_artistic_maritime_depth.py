"""Architectural custody tests; they make no native or visual acceptance claim."""
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from control_room.common import UserError
from tools.artistic_maritime_depth import (
    AIR, ENVELOPES, DepthPlan, admit_owner, payload, prepare, states, support_proof, validate,
)


def fixture(bases=None,**kwargs):
    registry={'seed':'synthetic-only','world_path':'synthetic-only','blocks':{
        AIR:{},'minecraft:dark_oak_planks':{},'minecraft:barrel':{},
        'minecraft:dark_oak_stairs':{'facing':['north'],'half':['top'],'shape':['straight'],'waterlogged':['false']}}}
    return DepthPlan(registry,bases or {name:{} for name in ENVELOPES},**kwargs)


class MaritimeDepthCustody(TestCase):
    def test_unknown_blocks_and_properties_cannot_become_native_claims(self):
        p=fixture();p.group='drowned-rose'
        with self.assertRaisesRegex(UserError,'Missing exact native'):
            p.put(1300,70,-1280,'invented:ornate_arch')
        with self.assertRaisesRegex(UserError,'Unsupported native'):
            p.put(1300,70,-1280,'minecraft:dark_oak_planks',facing='north')

    def test_known_furniture_and_native_entities_remain_protected(self):
        pos=(1300,70,-1280)
        p=fixture({'drowned-rose':{pos:'minecraft:barrel'}});p.group='drowned-rose'
        with self.assertRaisesRegex(UserError,'furniture/machinery/lighting'):
            p.put(*pos,'minecraft:dark_oak_planks')
        p=fixture({'drowned-rose':{pos:'minecraft:dark_oak_planks'}},protected={pos});p.group='drowned-rose'
        with self.assertRaisesRegex(UserError,'block entity'):
            p.put(*pos,AIR)

    def test_other_authored_owner_is_not_a_convenient_surface(self):
        pos=(1300,70,-1280)
        p=fixture({'drowned-rose':{},'separate-owner':{pos:'minecraft:dark_oak_planks'}});p.group='drowned-rose'
        with self.assertRaisesRegex(UserError,'separate authored structure'):
            p.put(*pos,AIR)

    def test_route_body_cell_refuses_even_a_small_structural_stair(self):
        pos=(1300,70,-1280);p=fixture(clearance={pos});p.group='drowned-rose'
        with self.assertRaisesRegex(UserError,'protected circulation'):
            p.stair(*pos,'north')
        p.put(*pos,AIR)

    def test_original_import_reservation_survives_an_accidentally_widened_envelope(self):
        p=fixture();p.group='drowned-rose'
        with patch.dict(ENVELOPES,{'drowned-rose':(1280,64,-1340,1314,88,-1265)}):
            with self.assertRaisesRegex(UserError,'Downloaded original'):
                p.put(1290,70,-1320,'minecraft:dark_oak_planks')

    def test_actual_craft_body_remains_excluded_independently_of_building_bounds(self):
        p=fixture();p.group='harbor'
        with patch.dict(ENVELOPES,{'harbor':(1180,60,-1280,1223,76,-1229)}):
            with self.assertRaisesRegex(UserError,'cog/tender body'):
                p.put(1194,64,-1254,'minecraft:dark_oak_planks')

    def test_a_floating_added_cluster_cannot_get_a_support_receipt(self):
        p=fixture();p.group='drowned-rose';pos=(1300,70,-1280)
        p.put(*pos,'minecraft:dark_oak_planks')
        with self.assertRaisesRegex(UserError,'no voxel support path'):support_proof(p)
        p.all[1300,71,-1280]='minecraft:dark_oak_planks'
        result=support_proof(p)
        self.assertEqual(result['voxel_supported_positions'],1)
        self.assertIn('UNVERIFIED',result['native_shapes_and_survival'])

    def test_full_existing_building_participates_in_material_rule(self):
        bases={name:{} for name in ENVELOPES}
        bases['drowned-rose']={(x,y,-1280):'minecraft:dark_oak_planks' for x in range(1291,1295) for y in range(64,67)}
        p=fixture(bases);p.group='drowned-rose'
        for x in range(1291,1295):p.put(x,67,-1280,'minecraft:dark_oak_planks')
        with self.assertRaisesRegex(ValueError,'complete depth composite'):validate(p)

    def test_overlay_does_not_mutate_immutable_base(self):
        pos=(1300,70,-1280);base={pos:'minecraft:dark_oak_planks'}
        p=fixture({'drowned-rose':base});p.group='drowned-rose';p.put(*pos,AIR)
        self.assertEqual(base[pos],'minecraft:dark_oak_planks')
        self.assertEqual(p.all[pos],'minecraft:dark_oak_planks')

    def test_native_plan_pair_has_exact_target_positions_and_no_tag_replay(self):
        p=fixture();before={(1300,70,-1280):AIR};after={(1300,70,-1280):'minecraft:dark_oak_planks'}
        a=json.loads(payload(p.registry,'f'*64,before,'test before'))
        b=json.loads(payload(p.registry,'f'*64,after,'test after'))
        self.assertEqual([row[:3] for row in a['blocks']],[row[:3] for row in b['blocks']])
        self.assertEqual(b['block_entities'],[]);self.assertEqual(b['commands'],[])
        self.assertEqual(states(b),after)

    def test_duplicate_base_positions_fail_before_any_native_use(self):
        with self.assertRaisesRegex(UserError,'Duplicate immutable'):
            states({'palette':[AIR],'blocks':[[1,2,3,0],[1,2,3,0]]})

    def test_official_home_is_refused_before_any_output(self):
        with self.assertRaisesRegex(UserError,'separately owned artistic'):
            prepare(Path(r'D:\A World for Two'),'fictional-checkpoint','f'*64)

    def test_current_receipt_does_not_replace_owner_checkpoint_custody(self):
        home=Path(r'D:\A World for Two\staging\world-tests\fictional-only').resolve()
        owner={'format':'awft-artistic-stage:1','home':str(home),'backup':'old','backup_sha256':'a'*64}
        receipt={'verified':True,'id':'current','sha256':'b'*64}
        with self.assertRaisesRegex(UserError,'not reconciled'):
            admit_owner(home,owner,receipt,'current','b'*64)
        owner.update(backup='current',backup_sha256='b'*64)
        admit_owner(home,owner,receipt,'current','b'*64)
