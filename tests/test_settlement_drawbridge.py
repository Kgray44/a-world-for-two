import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_room.common import UserError, digest
from tools.settlement_drawbridge import (
    DEFAULT_OPEN_ANGLE, PHYSICAL_SHA, clearance_estimate, engineering_configuration,
    open_angle, placed_radios, placed_systems, prepare_engineering,
)


def fixture():
    blocks={}
    for system in placed_systems():
        for key,block in (('bearing','create:mechanical_bearing'),
                          ('sequencer','create:sequenced_gearshift'),('wheel','create:water_wheel')):
            blocks[tuple(system[key])]=block
        low,high=system['glue_min'],system['glue_max']
        for x in range(low[0],high[0]+1):
            for z in range(low[2],high[2]+1):
                blocks[x,70,z]='minecraft:stripped_dark_oak_log' if z==system['bearing'][2] else 'minecraft:dark_oak_planks'
    for pos in ((1182,73,-1178),(1182,73,-1110)):
        blocks[pos]='minecraft:stone_button'
    for row in placed_radios():
        blocks[tuple(row['position'])]='create:redstone_link'
    palette=sorted(set(blocks.values()))
    physical={'format':'awft-native-settlement:1','seed':'test-seed','world_path':'test-world',
              'palette':palette,'blocks':[[*pos,palette.index(state)] for pos,state in blocks.items()]}
    registry={'seed':'test-seed','world_path':'test-world','items':['minecraft:compass','minecraft:iron_nugget']}
    proof={'operation':'verify','plan_sha256':PHYSICAL_SHA,'failures':0,'finished':'2026-01-01T00:00:00Z'}
    backup={'verified':True,'sha256':'a'*64,'id':'synthetic-backup'}
    return registry,backup,proof,physical


class DrawbridgeEngineeringTests(unittest.TestCase):
    def test_owner_angle_range_and_integer_native_instruction_are_enforced(self):
        self.assertEqual(DEFAULT_OPEN_ANGLE,55)
        for value in (45,55,60):
            self.assertEqual(open_angle(value),value)
        for value in (True,False,44,61,90,55.0,float('nan'),'55'):
            with self.assertRaises(UserError):
                open_angle(value)

    def test_default_has_opposed_real_targets_and_exact_preserved_geometry(self):
        arguments=fixture();before=copy.deepcopy(arguments)
        plan=engineering_configuration(*arguments)
        self.assertEqual([s['expected_open_angle'] for s in plan['systems']],[-55,55])
        self.assertEqual([s['open_negative'] for s in plan['systems']],[True,False])
        self.assertEqual(plan['construction_sha256'],PHYSICAL_SHA)
        self.assertEqual(plan['backup_sha256'],'a'*64)
        self.assertEqual(plan['radios'],placed_radios())
        self.assertEqual(arguments,before)

    def test_custom_allowed_angle_changes_only_targets_and_geometric_estimates(self):
        plan=engineering_configuration(*fixture(),angle=45)
        self.assertEqual(plan['open_angle_degrees'],45)
        self.assertEqual([s['expected_open_angle'] for s in plan['systems']],[-45,45])
        self.assertEqual([s['bearing'] for s in plan['systems']],[[1199,70,-1172],[1199,70,-1116]])
        self.assertEqual([s['glue_min'] for s in plan['systems']],[[1187,69,-1172],[1187,69,-1143]])

    def test_failed_or_other_physical_proof_cannot_authorize_program_changes(self):
        for replacement in ({'failures':1},{'plan_sha256':'b'*64},{'finished':None},{'operation':'place'}):
            registry,backup,proof,physical=fixture();proof.update(replacement)
            with self.assertRaises(UserError):
                engineering_configuration(registry,backup,proof,physical)

    def test_current_backup_and_exact_declared_components_are_required(self):
        registry,backup,proof,physical=fixture()
        with self.assertRaises(UserError):
            engineering_configuration(registry,dict(backup,verified=False),proof,physical)
        with self.assertRaises(UserError):
            engineering_configuration(dict(registry,world_path='another-world'),backup,proof,physical)
        physical['blocks']=[row for row in physical['blocks'] if row[:3]!=[1199,70,-1172]]
        with self.assertRaisesRegex(UserError,'engineering components'):
            engineering_configuration(registry,backup,proof,physical)

    def test_nominal_clearance_is_explicitly_theoretical_and_decreases_at_lower_angle(self):
        low,selected=clearance_estimate(45),clearance_estimate(55)
        self.assertLess(low['nominal_deck_outer_edge_gap_blocks'],selected['nominal_deck_outer_edge_gap_blocks'])
        self.assertAlmostEqual(selected['nominal_north_far_center_y'],93.4363,places=3)
        self.assertIn('Unverified',selected['ship_clearance'])
        self.assertIn('excludes thickness',selected['scope'])

    def test_engineering_only_output_preserves_all_generic_files_and_physical_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);directory=home/'dashboard/settlement';directory.mkdir(parents=True)
            registry,backup,proof,physical=fixture()
            master=directory/('drawbridge-master-'+PHYSICAL_SHA+'.json')
            records={'registry.json':registry,'backup-receipt.json':backup,
                     'drawbridge-block-verification.json':proof,master.name:physical}
            for name,data in records.items():
                (directory/name).write_text(json.dumps(data),encoding='utf-8')
            protected=['plan.json','drawbridge-plan.json','drawbridge-manifest.json','engineering-plan.json']
            for name in protected:
                (directory/name).write_bytes(('preserve '+name).encode())
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            def recorded_hash(path):
                # The native master/proof are synthetic fixtures, not runtime evidence.
                return PHYSICAL_SHA if Path(path)==master else digest(path)
            with patch('tools.settlement_drawbridge.digest',side_effect=recorded_hash), \
                    patch('tools.settlement_drawbridge.Storage.reserve') as guard:
                result=prepare_engineering(home)
            self.assertEqual(guard.call_count,1)
            self.assertEqual(result['new_physical_placements'],0)
            self.assertEqual(result['construction_sha256'],PHYSICAL_SHA)
            for name,raw in before.items():
                self.assertEqual((directory/name).read_bytes(),raw)
            plan=Path(result['path'])
            self.assertEqual(hashlib.sha256(plan.read_bytes()).hexdigest(),result['sha256'])
            self.assertEqual(json.loads(plan.read_text())['open_angle_degrees'],55)
            self.assertEqual(len(list(directory.glob('drawbridge-engineering-55-*.json'))),2)


if __name__=='__main__':
    unittest.main()
