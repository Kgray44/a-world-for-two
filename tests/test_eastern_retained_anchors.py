import unittest
from control_room.common import UserError
from tools.artistic_eastern_retained_anchors import split_fields,RetainedCompound


class RetainedAnchorTests(unittest.TestCase):
    def test_actual_anchor_remains_context_but_cannot_be_placed(self):
        q=(1,2,3);a={q:'minecraft:cartography_table'};full={**a,(2,2,3):'minecraft:air'}
        context,delta=split_fields(full,a,[])
        self.assertEqual(context,full);self.assertNotIn(q,delta);self.assertEqual(full[q],a[q])

    def test_changed_anchor_or_tag_replay_is_refused(self):
        q=(1,2,3);a={q:'create:brown_toolbox[facing=west,waterlogged=false]'}
        with self.assertRaises(UserError):split_fields({q:'minecraft:air'},a,[])
        with self.assertRaises(UserError):split_fields(a,a,[{'position':list(q),'nbt':'{Items:[]}'}])

    def test_partial_toolbox_cannot_be_a_walk_floor(self):
        p=object.__new__(RetainedCompound)
        p.fixed={(1,0,3):'create:brown_toolbox[facing=west,waterlogged=false]'}
        p.blocks={**p.fixed,(1,1,3):'minecraft:air',(1,2,3):'minecraft:air',(2,0,3):'minecraft:spruce_planks'}
        self.assertFalse(p.open_cell((1,1,3)))
        self.assertTrue(p.open_cell((2,1,3)))
