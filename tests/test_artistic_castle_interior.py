"""Finite architectural custody checks; actual visual review remains separate."""
import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_castle_interior import AIR, BOUNDS, Interior, construct, decode, payload, state, validate
from tools.artistic_landmarks import construct as palace, payload as palace_payload


def registry():
    schema=json.loads((Path(__file__).parent/'fixtures/artistic_castle_interior_registry.json').read_text('utf-8'))
    return {'blocks':schema['blocks'],'seed':0,'world_path':'staging/synthetic-castle/world'}


class Saved:
    def __init__(self,original):
        self.original,self.overrides,self.protected=original,{},set()

    def state(self,pos):
        return self.overrides.get(pos,self.original.get(pos,AIR))


class CastleInteriorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=registry()
        source=palace(cls.registry,'castle-palace')
        cls.source=palace_payload(source,cls.registry,'a'*64,(1214,-1008),4)
        cls.original=decode(cls.source)
        cls.finish=construct(cls.registry,cls.source,Saved(cls.original))

    def changed(self):
        p=copy.copy(self.finish)
        p.blocks,p.previous=p.blocks.copy(),p.previous.copy()
        return p

    def test_complete_building_rule_and_original_functional_envelopes_hold(self):
        p=self.finish
        self.assertFalse(validate(p)['complete_palace_material_rule']['violations'])
        self.assertFalse(set(p.blocks)&p.fixed)
        for q in p.blocks:
            self.assertTrue(all(BOUNDS[n]<=v<=BOUNDS[n+3] for n,v in enumerate(q)))
        for q in p.fixed:
            self.assertEqual((p.original|p.blocks).get(q,AIR),p.original.get(q,AIR))
        self.assertLess(len(p.blocks),400)

    def test_chandelier_glazing_thrones_and_saved_entities_are_not_replayed(self):
        p=self.finish
        for q in ((1266,78,-1031),(1266,81,-1031),(1263,74,-1038),(1268,74,-1038)):
            self.assertNotIn(q,p.blocks)
        for q,v in p.original.items():
            if v.startswith(('handcrafted:','mcwwindows:','mcwlights:')):
                self.assertNotIn(q,p.blocks)
        saved=Saved(self.original);q=(1258,81,-1035);saved.protected.add(q)
        with self.assertRaisesRegex(UserError,'saved block entity'):
            Interior(self.registry,self.original,saved).put(*q,'chipped:engraved_calcite')

    def test_foreign_preimage_unknown_native_properties_and_scope_escape_refuse(self):
        q=(1258,81,-1035);saved=Saved(self.original);saved.overrides[q]='minecraft:chest[facing=north]'
        with self.assertRaisesRegex(UserError,'predecessor changed'):
            Interior(self.registry,self.original,saved).put(*q,'chipped:engraved_calcite')
        p=Interior(self.registry,self.original,Saved(self.original))
        with self.assertRaisesRegex(UserError,'circulation'):
            p.put(1266,74,-1030,'chipped:engraved_calcite')
        with self.assertRaisesRegex(UserError,'escaped'):
            p.put(1303,78,-1000,'chipped:engraved_calcite')
        with self.assertRaisesRegex(UserError,'exact audience-chamber state'):
            state(self.registry,'minecraft:smooth_quartz_slab',type='invented',waterlogged=False)

    def test_coffers_attach_to_retained_upper_floor_and_flow_is_unchanged(self):
        p=self.finish
        for q in p.groups['Joined timber coffers, ivory recesses and carved bosses']:
            if q[1]==81:
                self.assertNotEqual(p.original.get((q[0],82,q[2]),AIR),AIR)
        for z in (-1037,-1025):
            for x in (1258,1273):
                self.assertIn((x,77,z),p.blocks)
                adjacent=(x-1 if x==1258 else x+1,77,z)
                self.assertNotEqual((p.original|p.blocks).get(adjacent,AIR),AIR)
        for route in p.routes:
            x,y,z=route['feet']
            self.assertFalse({(x,y+dy,z) for dy in (-1,0,1)}&p.blocks.keys())

    def test_rule_cannot_be_evaded_by_different_state_or_facing(self):
        p=self.changed()
        for x in range(1260,1264):
            for z in range(-1034,-1030):
                q=(x,81,z)
                p.blocks[q]='minecraft:spruce_log[axis='+('x' if x%2 else 'z')+']'
                p.previous.setdefault(q,p.original[q])
        with self.assertRaisesRegex(ValueError,'material run rule'):
            validate(p)

    def test_native_payload_is_exact_delta_with_no_commands_entities_or_nbt(self):
        p=self.finish
        after=payload(p,p.blocks,'b'*64,'Synthetic proposed finish')
        before=payload(p,p.previous,'b'*64,'Synthetic exact preimage')
        self.assertEqual(set(p.blocks),set(p.previous))
        self.assertEqual(len(after['blocks']),len(before['blocks']))
        self.assertEqual(after['commands'],[])
        self.assertEqual(after['block_entities'],[])
        self.assertNotIn('entities',after)
        self.assertEqual(after['backup_sha256'],'b'*64)
        self.assertIn('PROPOSAL ONLY',after['validation'])


if __name__=='__main__':
    unittest.main()
