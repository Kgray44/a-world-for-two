"""Photo-finish custody and route fixtures; no native or artistic acceptance."""
import unittest

from control_room.common import UserError
from tools.artistic_lavender_promenade import GRAPE,Promenade,build,validate
from tools.artistic_lavender_promenade_finish import correction,PALETTE
from tools.settlement_attractions import base,properties
from test_lavender_promenade import registry,Snapshot


class FinishTests(unittest.TestCase):
    def fixture(self):
        r=registry();s=Snapshot();p=build(Promenade(r,s));validate(p)
        placed=p.blocks.copy();full=p.blocks|p.route|p.joins|p.retained
        gravel=(1296,65,-990);stairs=(1297,65,-967);root=(1297,66,-958)
        walk={gravel:'minecraft:gravel',stairs:'minecraft:stone_brick_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]',root:'minecraft:gravel'}
        full.update(walk)
        for q in walk:placed.pop(q,None)
        s.overrides.update(full)
        r['blocks'].update({'chipped:pink_concrete_tiles':{},'chipped:pink_concrete_panel':{},
                            'chipped:pink_concrete_pillar':{'axis':['x','y','z']}})
        return r,s,placed,full,walk,gravel,stairs,root

    def test_only_declared_materials_and_known_floors_change(self):
        r,s,p,f,w,g,st,root=self.fixture();d,b,support,final,groups,rule=correction(r,s,p,f,w)
        self.assertEqual(d[g],'chipped:checkered_calcite_tiles')
        self.assertEqual(base(d[st]),'create:cut_calcite_stairs')
        self.assertEqual(properties(d[st]),properties(w[st]))
        self.assertEqual(groups['pale_route_floor'],2)
        self.assertNotIn(root,d);self.assertNotIn(GRAPE,d)
        self.assertEqual(final[GRAPE],f[GRAPE]);self.assertEqual(support[root],w[root])
        for q,new in d.items():
            self.assertIn(q,f);self.assertEqual(b[q],f[q])
            if q not in (g,st):self.assertEqual(base(new),PALETTE[base(f[q])])
        self.assertEqual(rule['violations'],[])

    def test_sparse_original_path_air_is_qualified_from_actual_saved_body(self):
        r,s,p,f,w,g,st,root=self.fixture()
        self.assertNotIn((g[0],g[1]+1,g[2]),w)
        d,b,support,final,groups,rule=correction(r,s,p,f,w)
        self.assertEqual(support[g[0],g[1]+1,g[2]],'minecraft:air')
        self.assertEqual(support[g[0],g[1]+2,g[2]],'minecraft:air')

    def test_changed_source_and_air_named_BE_refuse(self):
        for kind in ('changed','BE'):
            r,s,p,f,w,g,st,root=self.fixture()
            q=next(q for q,v in p.items() if 'pink_terracotta_tiles' in v)
            if kind=='changed':s.overrides[q]='minecraft:air'
            else:s.protected.add(q)
            with self.subTest(kind=kind),self.assertRaises(UserError):correction(r,s,p,f,w)

    def test_unqualified_body_or_substrate_refuses(self):
        for dy in (1,-1):
            r,s,p,f,w,g,st,root=self.fixture();q=g[0],g[1]+dy,g[2]
            f.pop(q,None);s.overrides[q]='minecraft:water[level=0]'
            with self.subTest(dy=dy),self.assertRaises(UserError):correction(r,s,p,f,w)

    def test_old_floor_ownership_mismatch_is_not_resurfacing_authority(self):
        r,s,p,f,w,g,st,root=self.fixture();w[g]='minecraft:dirt_path'
        with self.assertRaisesRegex(UserError,'no longer retained'):correction(r,s,p,f,w)

    def test_missing_real_material_is_not_silently_substituted(self):
        r,s,p,f,w,g,st,root=self.fixture();del r['blocks']['chipped:pink_concrete_panel']
        with self.assertRaisesRegex(UserError,'Missing installed'):correction(r,s,p,f,w)


if __name__=='__main__':unittest.main()
