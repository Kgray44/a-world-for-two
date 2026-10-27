import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_depth_castle_mill import (AIR, Depth, MASONRY, basis, canonical_window_joins, mill,
    oriel, supported_geometry, validate)
from tools.settlement_attractions import base, properties


class Saved:
    def __init__(self,states):self.states=states;self.protected=set()
    def state(self,p):return self.states.get(p,AIR)


def masonry(x,y,z):
    return MASONRY[(1 if y%4==0 else 0)+(2 if x%4==0 else 0)+(4 if z%4==0 else 0)]


class PhysicalDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/physical_depth_registry.json').read_text('utf-8'))

    def facade(self,face='north'):
        center=(1260,75,-1041) if face=='north' else (1275,75,-1030)
        q=basis(center,face);states={}
        for u in range(-4,5):
            for dy in range(-3,9):
                p=q(u,dy);states[p]=masonry(*p)
        for u,col in ((-1,'r'),(0,'m'),(1,'l')):
            for dy,row in ((0,'bot'),(1,'mid'),(2,'top')):
                states[q(u,dy)]='mcwwindows:quartz_window[facing='+('north' if face=='north' else 'east')+',part='+row+'_'+col+']'
        # The real, pinned predecessor has this proud sill already. The new
        # two-block sill joins it; a bare flat-wall fixture lacks that support.
        for u in range(-2,3):
            states[q(u,-1,1)]=('chipped:carved_calcite' if u==0 else
                'minecraft:smooth_quartz_slab[type=top,waterlogged=false]' if face=='north' else
                'minecraft:polished_andesite_slab[type=top,waterlogged=false]')
        return Depth('castle',self.registry,states,Saved(states)),center

    def test_real_oriel_moves_all_glazing_and_preserves_every_original_native_property(self):
        p,center=self.facade();q=basis(center,'north')
        original={q(u,dy):p.actual(q(u,dy)) for u in (-1,0,1) for dy in range(3)}
        oriel(p,center,'north',3,'Synthetic facade')
        for old,state in original.items():
            new=(old[0],old[1],old[2]-1)
            self.assertEqual(p.blocks[old],AIR)
            self.assertEqual(p.blocks[new],state)
            self.assertEqual(p.previous[old],state)
        self.assertEqual(p.bays[0]['corbelled_sill_and_crown_depth'],2)
        self.assertGreater(len(supported_geometry(p)),30)
        self.assertTrue(any(v[2]==center[2]-2 for v in p.real_added))

    def test_east_facing_arch_steps_follow_the_window_width_in_z(self):
        p,center=self.facade('east');q=basis(center,'east')
        oriel(p,center,'east',3,'Synthetic east facade')
        self.assertEqual(properties(p.blocks[q(-2,3,2)])['facing'],'south')
        self.assertEqual(properties(p.blocks[q(2,3,2)])['facing'],'north')
        supported_geometry(p)

    def test_canonical_native_window_edges_correct_old_placeholders_without_geometry_changes(self):
        p,center=self.facade();q=basis(center,'north')
        for u in (-1,1):
            for dy in range(3):
                pos=q(u,dy);value=p.snapshot.states[pos]
                p.snapshot.states[pos]=value.replace('_r]','_l]') if u==-1 else value.replace('_l]','_r]')
        oriel(p,center,'north',3,'Synthetic old placeholder')
        before=p.blocks.copy();updates,changes=canonical_window_joins(p.original|p.blocks,p.blocks,self.registry)
        self.assertEqual(len(changes),6)
        self.assertEqual(properties(updates[q(-1,0,1)])['part'],'bot_r')
        self.assertEqual(properties(updates[q(1,2,1)])['part'],'top_l')
        self.assertEqual(p.blocks,before)
        for pos,value in updates.items():
            self.assertEqual(base(value),base(before[pos]))
            self.assertEqual({k:v for k,v in properties(value).items() if k!='part'},
                             {k:v for k,v in properties(before[pos]).items() if k!='part'})

    def test_saved_block_entities_route_air_fluids_and_existing_doors_refuse(self):
        p,center=self.facade();q=basis(center,'north')
        p.snapshot.protected.add(q(0))
        with self.assertRaisesRegex(UserError,'saved block entity'):
            p.set(q(0),AIR,replace_glazing=True)
        p.snapshot.protected.clear();p.route('Existing route',[q(0,0,1)])
        with self.assertRaisesRegex(UserError,'route'):
            p.put(q(0,0,1),'chipped:small_calcite_bricks')
        p,center=self.facade();outside=(1260,75,-1043);p.snapshot.states[outside]='minecraft:water[level=0]'
        with self.assertRaisesRegex(UserError,'conflicts'):
            p.put(outside,'chipped:small_calcite_bricks')
        door=(1261,75,-1043);p.snapshot.states[door]='minecraft:oak_door[facing=north,half=lower,hinge=left,open=false,powered=false]'
        p.fixed.add(door)
        with self.assertRaises(UserError):p.put(door,'chipped:small_calcite_bricks')

    def test_existing_masonry_is_adopted_and_never_counted_as_new_depth_recolor(self):
        p,center=self.facade();q=basis(center,'north');pos=q(3)
        old=p.actual(pos)
        p.put(pos,'chipped:carved_calcite')
        self.assertNotIn(pos,p.blocks)
        self.assertNotIn(pos,p.real_added)
        self.assertEqual(p.adopted[pos],old)

    def test_unanchored_new_geometry_refuses_without_a_fake_support_claim(self):
        p,_=self.facade();p.put((1280,110,-1000),'chipped:small_calcite_bricks')
        with self.assertRaisesRegex(UserError,'support path'):supported_geometry(p)

    def test_material_rule_checks_complete_predecessor_not_only_the_layer(self):
        states={(1250+x,100,-1000):'minecraft:oak_door[facing='+('north' if x%2 else 'east')+
                ',half=lower,hinge=left,open=false,powered=false]' for x in range(10)}
        p=Depth('castle',self.registry,states,Saved(states))
        with self.assertRaisesRegex(ValueError,'material run rule'):validate(p)

    def test_supported_balcony_has_actual_access_and_preserves_original_two_block_aisle(self):
        states={}
        for x in range(1308,1325):
            for z in range(-1006,-986):states[x,67,z]=masonry(x,67,z)
        for x in range(1310,1323):
            for y in range(68,79):states[x,y,-990]=masonry(x,y,-990)
        for z in (-1004,-997,-992):
            for x in range(1310,1323):states[x,73,z]=masonry(x,73,z)
        for x,part in ((1315,'r'),(1316,'l')):
            for y,row in ((76,'bot'),(77,'top')):
                states[x,y,-990]='mcwwindows:dark_oak_plank_window[facing=north,part='+row+'_'+part+']'
        p=Depth('mill',self.registry,states,Saved(states))
        p.route('Original two-wide mill aisle',[(1316,68,-991),(1317,68,-991)],headroom=2)
        mill(p)
        checks=validate(p)
        self.assertEqual(checks['machine_and_route_targets'],0)
        self.assertEqual(checks['removed_or_relocated_glazing_cells'],4)
        self.assertFalse(set(p.blocks)&p.fixed)
        for y in range(68,76):
            self.assertEqual(base(p.blocks[1314,y,-991]),'minecraft:ladder')
            self.assertEqual(base(p.blocks[1315,y,-991]),'chipped:reinforced_stripped_spruce_log')
        self.assertEqual(base(p.blocks[1315,76,-990]),'mcwdoors:dark_oak_glass_door')
        self.assertEqual(properties(p.blocks[1315,76,-990])['hinge'],'left')
        self.assertEqual(properties(p.blocks[1316,76,-990])['hinge'],'right')
        self.assertEqual(p.at((1316,68,-991)),AIR)
        self.assertEqual(p.at((1317,69,-991)),AIR)


if __name__=='__main__':unittest.main()
