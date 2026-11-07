"""Original small fixtures for the actual one-plane/closure regression."""
import json,unittest
from pathlib import Path
from tools import artistic_eastern_compound_sprint as e
from tools.artistic_eastern_roof_volume import roof_surface,dormer_surfaces


class ClosedEasternRoofs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/eastern_compound_registry.json').read_text())

    def build(self,intent):
        mass={'bounds_xz':[0,0,10,18],'floor_y':64,'storeys':2,'roof':intent}
        spec={'id':'roof-regression','name':'Original Roof Regression','program':'charts','masses':[mass],
              'actual_building_floor_columns_xz':[[x,z]for x in range(11)for z in range(19)]}
        return e.build(self.registry,spec,{'fixed':{},'bes':set(),'retire':{}},set(),{(x,-2)for x in range(-1,12)})

    def test_former_single_plane_is_now_two_real_opposite_pitches(self):
        p=self.build('low side-hung dark shingle');e.validate(p)
        faces={e.properties(v).get('facing')for q,v in p.blocks.items()
               if e.key(v)=='mcwroofs:dark_oak_roof'and'roof facet'in p.roles.get(q,'')}
        self.assertTrue({'east','west'}<=faces)
        self.assertLessEqual(max(q[1]for q in p.blocks),p.top_levels[0]+6)
        self.assertTrue(p.roof_volume_details[0]['ridge_closed'])
        self.assertEqual(e.audit_entry_states(p.registry,p.entries,p.blocks)['real_matching_door_pairs'],1)

    def test_dormer_unions_raise_front_roof_and_keep_the_hidden_sheet_absent(self):
        surface=roof_surface((-1,-1,11,19),8,'gable','x');before={q:r['y']for q,r in surface.items()}
        dormers=dormer_surfaces(surface,(-1,-1,11,19),8,'x',0)
        self.assertEqual(len(dormers),2)
        self.assertTrue(any(surface[q]['y']>before[q]for q in surface))
        self.assertTrue(all(isinstance(v['y'],int)for v in surface.values()))
        p=self.build('weathered hipped clay');proof=e.validate(p)
        self.assertTrue(proof['all_source_solids_connected_to_proposed_plinths'])
        self.assertTrue(p.roof_volume_details[0]['dormers'])
        self.assertTrue(p.endwall_relief)

    def test_clipped_ends_keep_all_furnishing_and_material_constraints(self):
        p=self.build('offset halfhip');proof=e.validate(p)
        self.assertEqual(proof['complete_material_rule']['violations'],[])
        self.assertTrue(proof['actual_entry_states']['real_matching_door_pairs'])
        for room in p.rooms:
            for obj in room['actual_objects']:
                self.assertEqual(p.blocks[tuple(obj['position'])],obj['expected_state'])


if __name__=='__main__':unittest.main()
