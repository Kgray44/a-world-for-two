"""Actual planned door/body geometry controls tiny alleys; not screenshots."""
import json
from pathlib import Path
import unittest
from control_room.common import UserError
from tools.artistic_tortuga_clusters import CLUSTERS,construct
from tools.artistic_create_substrate import qualified_mount,JAR_SHA,CLASS_SHA


class TortugaClusterTests(unittest.TestCase):
    def setUp(self):
        self.registry=json.loads((Path(__file__).parent/'fixtures/tortuga_frontages_registry.json').read_text())
        self.free={(x,z)for x in range(1155,1202)for z in range(-1242,-1204)}

    def test_four_distinct_masses_keep_actual_short_two_wide_circulation(self):
        s,_,b,main,lane,routes=construct(self.registry,CLUSTERS['quill-court'],self.free)
        self.assertEqual(len(b),4);self.assertEqual(len({q['recipe']for q in b}),4)
        self.assertEqual(sum(len(q['rooms'])for q in b),9)
        self.assertGreater(len(main),3*len(lane))
        self.assertFalse(main&set(lane))
        for x,z in lane:self.assertTrue(all(s.get((x,y,z),'minecraft:air')=='minecraft:air'for y in(64,65)))
        tea=next(v for v in b if v['recipe']=='mugs-mending')
        self.assertEqual({r['outward']for r in tea['entries']},{'north','west'})
        # The old low bookshop knee was a real obstacle. The new tall native
        # casement keeps its carved bracket above literal actor headroom.
        self.assertNotIn('curved_corbel',s.get((1175,65,-1224),''))
        self.assertIn('curved_corbel',s[1175,66,-1224])

    def test_water_or_unknown_in_an_entire_main_outline_refuses_before_roads(self):
        self.free.remove((1164,-1231))
        with self.assertRaisesRegex(UserError,'main outline is not completely qualified'):
            construct(self.registry,CLUSTERS['quill-court'],self.free)

    def test_narrow_native_zinc_factory_proof_never_qualifies_other_mods_or_water(self):
        proof={'artifact_sha256':JAR_SHA,'class_sha256':CLASS_SHA,'factory_class':'net/minecraft/world/level/block/Block','factory_handle_kind':8}
        lookup=lambda x,y,z:'minecraft:gravel'if y==62 else'create:zinc_ore'
        self.assertTrue(qualified_mount(lookup,0,0,proof)['stable'])
        with self.assertRaisesRegex(UserError,'exact reviewed installed native factory'):
            qualified_mount(lookup,0,0,{})
        for end in('minecraft:water[level=0]','minecraft:air','example:unqualified_ore'):
            self.assertFalse(qualified_mount(lambda x,y,z:'minecraft:gravel'if y==62 else end,0,0,proof)['stable'])


if __name__=='__main__':unittest.main()
