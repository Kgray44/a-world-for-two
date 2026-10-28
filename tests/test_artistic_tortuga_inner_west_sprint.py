"""Occupied tight lots, actual route custody and source-only registration."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from tools import artistic_tortuga_inner_west_sprint as west
from tools.artistic_tortuga_frontages import RECIPES,AIR,check,key
from tools.artistic_tortuga_variants import variant_of


class InnerWestSprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/tortuga_fill_registry.json').read_text())

    def test_distinct_occupied_proportions_have_real_supported_furnished_scenes(self):
        shapes=set();storeys=set()
        for name,factory in west.CUSTOM.items():
            p=factory(self.registry);proof=check(p);m=p.main[p.owner]
            shapes.add((max(x for x,z in m)-min(x for x,z in m)+1,max(z for x,z in m)-min(z for x,z in m)+1))
            storeys.add(proof['storeys'])
            self.assertGreaterEqual(proof['rooms'],2)
            self.assertEqual(proof['material']['violations'],[])
            self.assertTrue(any(key(s).startswith('mcwwindows:')for s in p.blocks.values()))
            self.assertTrue(any(key(s).startswith(('minecraft:crafting_table','minecraft:loom','minecraft:cartography_table','minecraft:smoker','minecraft:stonecutter'))for s in p.blocks.values()))
            self.assertFalse(any('Items:'in tag or'Owner:'in tag for tag in p.tags.values()))
            if proof['storeys']>1:
                self.assertTrue(any(key(s).endswith('_bed')for s in p.blocks.values()))
                self.assertTrue(any(r['kind']=='stairs'for r in p.routes))
        self.assertGreaterEqual(len(shapes),6)
        self.assertEqual(storeys,{1,2})

    def test_rotations_preserve_real_routes_door_halves_and_furniture(self):
        for name in('iw-short-watch','iw-chart-sliver','iw-spindle-return','iw-low-supper','iw-tackle-sliver'):
            for turn in range(4):
                p=variant_of(west.CUSTOM[name](self.registry),name,turn)
                self.assertEqual(check(p)['material']['violations'],[])
                with west.source_recipes():
                    states,tags,buildings,main=west.fill.modeled(self.registry,{'buildings':[{'recipe':name,'turn':turn,'name':name,'trade':'Working Trade','origin':[1100,63,-1250]}],'links':[]})
                self.assertEqual(len(buildings[0]['scene_views']),2)
                self.assertTrue(all(isinstance(value,str)for value in tags.values()))

    def test_registration_restores_every_original_on_failure(self):
        before=dict(RECIPES)
        with self.assertRaisesRegex(RuntimeError,'source interrupted'):
            with west.source_recipes():
                self.assertEqual(set(RECIPES)-set(before),set(west.CUSTOM))
                raise RuntimeError('source interrupted')
        self.assertEqual(RECIPES,before)

    def test_protected_air_and_existing_architecture_are_not_buildable_permission(self):
        p=SimpleNamespace(owner='test',main={'test':{(0,0)}},blocks={(0,0,0):'minecraft:stone'},entries=[])
        free={(1100,-1250)}
        self.assertIsNone(west.site_ok(p,(1100,63,-1250),free,{}, {},{(1100,63,-1250):AIR},set(),set()))
        self.assertIsNone(west.site_ok(p,(1100,63,-1250),free,{}, {(1100,63,-1250):'minecraft:stone'}, {},set(),set()))

    def test_future_public_route_never_clears_an_old_body_or_replays_new_paver(self):
        rows={(1100,-1250):[1100,-1250,'minecraft:dirt',AIR,AIR],(1101,-1250):[1101,-1250,'minecraft:dirt',AIR,AIR],(1102,-1250):[1102,-1250,'minecraft:dirt',AIR,AIR]}
        prior={(1100,63,-1250):'minecraft:andesite',(1101,64,-1250):'minecraft:barrel',(1102,63,-1250):'minecraft:andesite'}
        walking=west.safe_walking(rows,prior,{},set(),{}, {(1100,63,-1250):'minecraft:andesite'})
        self.assertEqual(set(walking),{(1100,-1250)})

    def test_private_threshold_can_use_owned_new_floor_but_never_clear_an_old_body(self):
        rows={(x,0):[x,0,'minecraft:gravel',AIR,AIR]for x in range(5)}
        rows[0,0]=[0,0,'minecraft:gravel','supplementaries:barnacles[down=true,east=false,north=false,south=false,up=false,waterlogged=false,west=false]',AIR]
        values={(0,63,0):'minecraft:stripped_spruce_wood[axis=x]',(0,64,0):AIR,(0,65,0):AIR}
        self.assertEqual(west.private_threshold_path((0,0),{(4,0)},rows,values,{(0,0)},set(),{},{}),[(x,0)for x in range(5)])
        blocked=dict(rows);blocked[2,0]=[2,0,'minecraft:gravel','minecraft:barrel',AIR]
        with self.assertRaisesRegex(Exception,'No supported short private'):
            west.private_threshold_path((0,0),{(4,0)},blocked,values,{(0,0)},set(),{},{})

    def test_private_passage_does_not_invent_floor_or_silently_extend_its_bound(self):
        rows={(x,0):[x,0,'minecraft:gravel',AIR,AIR]for x in range(12)}
        with self.assertRaisesRegex(Exception,'No supported short private'):
            west.private_threshold_path((0,0),{(11,0)},rows,{},set(),set(),{},{})
        rows[5,0]=[5,0,AIR,AIR,AIR]
        with self.assertRaisesRegex(Exception,'No supported short private'):
            west.private_threshold_path((0,0),{(11,0)},rows,{},set(),set(),{},{},max_steps=12)


if __name__=='__main__':unittest.main()
