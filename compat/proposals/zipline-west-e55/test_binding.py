"""Focused source-only binding tests, separate from the frozen source checkpoint.

Run explicitly from the repository with unittest discovery in this directory.
They do not start Java, a game, a native graph or a real container operation.
"""
import json
import unittest

from control_room.common import UserError
from tools.artistic_zipline_west_bind_e55 import (
    new_stock_tag,check_fresh_target,geometry_digest,BARREL,STOCK,
)


class SourceStockAdmission(unittest.TestCase):
    def test_existing_inventory_or_even_an_existing_matching_barrel_refuses(self):
        for actual,has_be in ((BARREL,True),(BARREL,False),('minecraft:air',True),('minecraft:cave_air',False)):
            with self.subTest(actual=actual,BE=has_be):
                with self.assertRaises(UserError):new_stock_tag(actual,has_be,BARREL,{'minecraft:chain':14})

    def test_only_the_exact_explicit_creative_quantity_is_initializable(self):
        for items in ({'minecraft:chain':13},{'minecraft:chain':15},{'minecraft:chain':14.0},{'minecraft:chain':14,'minecraft:diamond':1}):
            with self.assertRaises(UserError):new_stock_tag('minecraft:air',False,BARREL,items)
        with self.assertRaises(UserError):new_stock_tag('minecraft:air',False,'minecraft:chest[facing=north]',{'minecraft:chain':14})

    def test_real_snbt_syntax_and_modern_count_slot_types(self):
        try:import nbtlib
        except ImportError:self.skipTest('Optional existing read-only SNBT parser unavailable; no native parser acceptance inferred')
        tag=nbtlib.parse_nbt(new_stock_tag('minecraft:air',False,BARREL,{'minecraft:chain':14}))
        self.assertEqual(len(tag['Items']),1)
        item=tag['Items'][0]
        self.assertIsInstance(item['Slot'],nbtlib.Byte)
        self.assertEqual(int(item['Slot']),0)
        self.assertIsInstance(item['count'],nbtlib.Int)
        self.assertEqual(int(item['count']),14)
        self.assertEqual(str(item['id']),'minecraft:chain')
        self.assertNotIn('Count',item)
        self.assertIn('creative construction',json.loads(str(tag['CustomName']))['text'])

    def test_frozen_geometry_hash_is_order_independent_but_state_exact(self):
        a={(1,2,3):'minecraft:stone',(2,3,4):'minecraft:spruce_planks'}
        self.assertEqual(geometry_digest(a),geometry_digest(dict(reversed(list(a.items())))))
        self.assertNotEqual(geometry_digest(a),geometry_digest(a|{(2,3,4):'minecraft:oak_planks'}))

    def test_target_gate_preserves_authored_air_tree_water_be_and_unknown(self):
        for actual,be,authored in [('minecraft:air',False,{STOCK}),('minecraft:oak_log[axis=y]',False,set()),('minecraft:water[level=0]',False,set()),('minecraft:air',True,set()),(None,False,set()),(BARREL,False,set())]:
            with self.assertRaises(UserError):check_fresh_target(STOCK,actual,be,authored)
        check_fresh_target(STOCK,'minecraft:air',False,set())


if __name__=='__main__':unittest.main()
