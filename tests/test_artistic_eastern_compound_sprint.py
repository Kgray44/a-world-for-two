"""Synthetic original architecture fixtures; no copied world/stock arrays."""
from pathlib import Path
from collections import deque
from types import SimpleNamespace
import json
import unittest

from tools import artistic_eastern_compound_sprint as east


def spec(*,narrow=False,five=False):
    if narrow:
        masses=[{'bounds_xz':[0,0,2,7],'floor_y':64,'storeys':3,'roof':'offset halfhip'}]
    else:
        masses=[{'bounds_xz':[0,0,10,11],'floor_y':64,'storeys':3 if five else 2,'roof':'weathered hipped clay'},
                {'bounds_xz':[11,2,14,8],'floor_y':64,'storeys':1,'roof':'low side-hung dark shingle'},
                {'bounds_xz':[3,12,6,16],'floor_y':64,'storeys':2,'roof':'cross-gabled slate'}]
        if five:masses[0]['occupied_floor_offsets']=[0,5,10]
    cells=sorted({(x,z)for m in masses for x in range(m['bounds_xz'][0],m['bounds_xz'][2]+1)for z in range(m['bounds_xz'][1],m['bounds_xz'][3]+1)})
    return {'id':'synthetic-coastal-workshop','name':'Synthetic Coastal Workshop','program':'cloth','masses':masses,
            'actual_building_floor_columns_xz':[list(q)for q in cells]}


def empty_stock():return {'fixed':{},'bes':set(),'retire':{},'moves':[]}


class EasternCompoundSprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/eastern_compound_registry.json').read_text())

    def build(self,model,stock=None,other=()):
        return east.build(self.registry,model,stock or empty_stock(),set(other),{(x,-2)for x in range(-2,17)},0)

    def test_complete_joined_workshop_has_real_scenes_routes_three_roof_volumes(self):
        p=self.build(spec());proof=east.validate(p)
        self.assertEqual(proof['mass_count'],3)
        self.assertGreaterEqual(proof['furnished_scenes'],4)
        self.assertTrue(proof['all_source_solids_connected_to_proposed_plinths'])
        self.assertEqual(proof['complete_material_rule']['violations'],[])
        self.assertEqual(len({r['geometry']for r in p.roof_sections}),3)
        self.assertTrue(p.tags)
        self.assertFalse(any('Items'in json.dumps(v)or'Owner'in json.dumps(v)for v in p.tags.values()))

    def test_conserved_real_container_is_literal_and_never_in_new_tag_delta(self):
        value='minecraft:barrel[facing=up,open=false]';world=(2,65,2)
        stock={'fixed':{world:value},'bes':{world},'retire':{(3,64,2):'minecraft:spruce_planks'},'moves':[]}
        p=self.build(spec(),stock);east.validate(p);q=p.local(world)
        self.assertEqual(p.blocks[q],value)
        self.assertNotIn(q,p.tags)
        self.assertFalse(p.put(*q,'minecraft:air',role='deliberate invalid fixture replacement'))
        self.assertEqual(p.blocks[q],value)

    def test_narrow_three_storey_wing_uses_supported_ladder_without_partial_stair_fragments(self):
        p=self.build(spec(narrow=True));east.validate(p)
        self.assertEqual(p.stairs,[])
        ladders=[r for r in p.vertical if r['kind']=='native supported service ladder']
        self.assertEqual(len(ladders),1)
        for q,value in p.blocks.items():
            if east.key(value)!='minecraft:ladder':continue
            face=east.properties(value)['facing'];dx,dz=east.VEC[face]
            self.assertEqual(east.key(p.blocks[q[0]-dx,q[1],q[2]-dz]),'minecraft:dark_oak_wood')

    def test_single_aisle_service_floors_are_furnished_without_blocking_their_ladder_routes(self):
        p=self.build(spec(narrow=True));east.validate(p)
        self.assertEqual({(r['mass'],r['floor'])for r in p.rooms},{(0,0),(0,1),(0,2)})
        for room in p.rooms:
            self.assertTrue(room['actual_objects'])
            for obj in room['actual_objects']:
                q=tuple(obj['position']);self.assertNotIn(q,p.body)
                self.assertEqual(p.blocks[q],obj['expected_state'])
        self.assertTrue(all(east.key(p.blocks.get(q,'minecraft:air'))in east.VOID or east.key(p.blocks[q]).endswith('_door')for q in p.body))

    def test_reviewed_five_metre_levels_get_genuine_five_riser_stairs_and_higher_ceiling(self):
        p=self.build(spec(five=True));east.validate(p)
        five=[r for r in p.vertical if r['kind']=='native ordinary stair'and r['risers']==5]
        self.assertGreaterEqual(len(five),2)
        self.assertTrue(all(len(row['blocks'])==5 for row in five))
        self.assertEqual(p.floor_levels[0],[0,5,10])
        self.assertEqual(p.top_levels[0],14)

    def test_preserved_planter_gets_real_sill_and_reserved_floor_cannot_be_cut_for_later_detail(self):
        world=(3,66,3);stock={'fixed':{world:'minecraft:potted_fern'},'bes':set(),'retire':{},'moves':[]}
        p=self.build(spec(),stock);east.validate(p)
        self.assertEqual(east.key(p.blocks[3,1,3]),'minecraft:dark_oak_planks')
        q=next(iter(p.route_floor_points));before=p.blocks[q]
        self.assertFalse(p.put(*q,'minecraft:air',role='deliberate unsupported-route mutation'))
        self.assertEqual(p.blocks[q],before)

    def test_core_model_skirt_clips_new_projections_without_changing_approved_ground_mass(self):
        model=spec();protected={(-1,z)for z in range(-1,19)}
        p=self.build(model,other=protected);east.validate(p)
        self.assertFalse(any((x,z)in protected for x,y,z in p.blocks))
        self.assertEqual(p.footprint,set(map(tuple,model['actual_building_floor_columns_xz'])))

    def test_a_real_ladder_connects_both_clear_sides_on_each_actual_floor(self):
        cells={(x,z)for x in range(3)for z in range(5)};blocks={}
        for level in(0,4):
            for x,z in cells:blocks[x,level,z]='minecraft:spruce_planks'
            for x,z in east.boundary(cells):
                for y in range(level+1,level+4):blocks[x,y,z]='minecraft:dark_oak_planks'
        for y in range(1,7):
            blocks[1,y,2]='minecraft:ladder[facing=east,waterlogged=false]'
            blocks[0,y,2]='minecraft:dark_oak_wood[axis=y]'
        p=SimpleNamespace(blocks=blocks,mass_fields=[cells],floor_levels=[[0,4]],spec={'masses':[{}]},
            vertical=[{'kind':'native supported service ladder','shaft':[[1,y,2]for y in range(1,7)],'floor_levels':[0,4]}])
        p.open_cell=lambda q:east.Compound.open_cell(p,q)
        graph=east.walking_graph(p);seen={(1,1,3)};todo=deque(seen)
        while todo:
            for q in graph[todo.popleft()]:
                if q not in seen:seen.add(q);todo.append(q)
        self.assertEqual(seen,{(1,y,z)for y in(1,5)for z in(1,3)})

    def test_conserved_non_entity_job_station_stays_literal_with_a_connected_visit(self):
        world=(2,65,2);stock={'fixed':{world:'minecraft:cartography_table'},'bes':set(),'retire':{},'moves':[]}
        p=self.build(spec(),stock);proof=east.validate(p)
        self.assertEqual(p.blocks[p.local(world)],'minecraft:cartography_table')
        self.assertEqual(proof['preserved_functional_nonBE_positions'],1)
        self.assertTrue(any(abs(q[0]-2)+abs(q[2]-2)<=3 and q[1]==1 for q in p.circulation['mass_floor_visiting_points']))

    def test_large_cross_gables_have_structural_studs_and_pass_complete_material_rule(self):
        model=spec();model['masses']=[{'bounds_xz':[0,0,12,14],'floor_y':64,'storeys':1,'roof':'cross-gabled slate'}]
        model['actual_building_floor_columns_xz']=[[x,z]for x in range(13)for z in range(15)]
        p=self.build(model);proof=east.validate(p)
        self.assertTrue(any('upright gable stud'in role for role in p.roles.values()))
        self.assertEqual(proof['complete_material_rule']['violations'],[])


if __name__=='__main__':unittest.main()
