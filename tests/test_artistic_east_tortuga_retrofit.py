"""Meaningful preservation gates for one source-only eastern correction."""
import json
import unittest

import nbtlib

from control_room.common import UserError
from tools.artistic_captains_hall import native_payload
from tools.artistic_east_tortuga_retrofit import EXACT, JOIN, shell_replacement_allowed, with_exact_be_tags


class EastTortugaCustodyTests(unittest.TestCase):
    def test_only_exact_owned_shell_can_change_and_state_or_human_deltas_refuse(self):
        q=(1237,76,-1208);old='mcwroofs:spruce_roof[facing=east,half=bottom,shape=straight]'
        source={q:old};ledger={q:{'classification':EXACT,'actual_saved':old}}
        self.assertEqual(shell_replacement_allowed(q,old,'minecraft:air',source,ledger,set(),set()),'EXACT_UNCHANGED_OWNED_ARCHITECTURE')
        for actual,classification in ((old.replace('straight','inner_left'),EXACT),(old,JOIN),('minecraft:barrel',EXACT)):
            with self.subTest(actual=actual,classification=classification),self.assertRaises(UserError):
                shell_replacement_allowed(q,actual,'minecraft:air',source,{q:{'classification':classification,'actual_saved':actual}},set(),set())
        for protected,walk in (({q},set()),(set(),{q})):
            with self.assertRaises(UserError):shell_replacement_allowed(q,old,'minecraft:air',source,ledger,protected,walk)

    def test_existing_full_nbt_stays_verification_only_with_exact_numeric_types(self):
        q=(1234,65,-1207)
        be=nbtlib.parse_nbt('{id:"minecraft:barrel",x:1234,y:65,z:-1207,Items:[{Slot:0b,id:"minecraft:paper",count:3,components:{"minecraft:custom_data":{marker:7s}}}]}')
        raw=native_payload({'seed':'synthetic','world_path':'synthetic-only'},{q:'minecraft:barrel[facing=up,open=false]'},'a'*64,'Verify retained synthetic fixture only')
        result=json.loads(with_exact_be_tags(raw,{q:be}))
        self.assertTrue(result['construction_forbidden'])
        restored=nbtlib.parse_nbt(result['block_entities'][0]['nbt'])
        self.assertIs(type(restored['Items'][0]['Slot']),nbtlib.Byte)
        self.assertIs(type(restored['Items'][0]['components']['minecraft:custom_data']['marker']),nbtlib.Short)
        self.assertEqual(restored,be)


if __name__=='__main__':
    unittest.main()
