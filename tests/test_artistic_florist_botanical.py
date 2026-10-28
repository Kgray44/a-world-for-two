"""Source geometry/support checks; no claim of native plant survival or art."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools import artistic_botanical as bot
from tools import artistic_florist_botanical as art
from tools import artistic_north_bank_west as west
from tools.artistic_materials import require_material_rule,require_outdoor_rule

FIXTURES=Path(__file__).parent/'fixtures'
REGISTRY=json.loads((FIXTURES/'north_bank_west_registry.json').read_text())
REGISTRY['blocks'].update(json.loads((FIXTURES/'florist_botanical_registry.json').read_text())['blocks'])


def source_field():
    # This is the original source compositor, not an MCA fixture or an alleged
    # real-world clear field. Actual prepare() separately requires e55preimages.
    shop=west.florist(REGISTRY);authored=west.world_blocks(shop,(1081,-1249),64,0)
    saved_bes={(1081+x,64+y,-1249+z) for x,y,z in shop.tags}
    def current(p):return authored.get(p,'minecraft:stone' if p[1]<=63 else 'minecraft:air')
    reserved={p for p,s in authored.items() if bot.key(s) in bot.AIR}
    passage={(x,y,z) for x in (1091,1092) for z in range(-1245,-1238) for y in (64,65)}
    reserved.update(passage)
    return bot.Garden(REGISTRY,current,saved_bes,reserved,set()),authored,passage


class FloristBotanicalPilot(unittest.TestCase):
    def test_complete_furnished_shop_and_two_wide_side_alley_are_preserved(self):
        g,owner,passage=source_field();before=dict(owner);art.construct(g)
        self.assertEqual(owner,before)
        self.assertFalse(set(g.blocks)&(set(owner)|passage|g.saved_bes))
        require_material_rule(owner|g.blocks,'Whole original furnished florist plus pilot')
        require_outdoor_rule(owner|g.blocks,'Whole shop and side garden')
        self.assertLessEqual(len(g.blocks),200)
        self.assertGreaterEqual(len(g.scenes),10)
        self.assertTrue(any(s.startswith('regions_unexplored:potted_') for s in g.blocks.values()))
        self.assertTrue(any(s.startswith('fishofthieves:potted_') for s in g.blocks.values()))

    def test_refused_late_window_pot_leaves_no_half_ledge_or_extra_root(self):
        g,_,_=source_field();g.reserved_body.add((1084,67,-1251))
        with self.assertRaises(UserError):art.flowered_ledge(g)
        self.assertEqual(g.blocks,{})
        self.assertEqual(g.previous,{})
        self.assertEqual(g.roots,{})
        self.assertEqual(g.scenes,[])

    def test_ivy_needs_the_actual_correct_side_face_for_every_segment(self):
        g,owner,_=source_field()
        # The lowest wall is present but one higher native attachment is gone.
        current=g.current
        g.current=lambda p:'minecraft:air' if p==(1081,66,-1249) else current(p)
        with self.assertRaises(UserError):art.attached_ivy(g,(1081,65,-1250),'north',3)
        self.assertEqual(g.blocks,{})
        self.assertEqual(g.roots,{})

    def test_leaf_garland_has_face_adjacent_log_paths_and_refuses_floating_leaf(self):
        states={(0,0,0):art.NEW_LOG+'[axis=y]',(0,1,0):'minecraft:cherry_leaves',(1,1,0):'regions_unexplored:flowering_leaves'}
        self.assertEqual(art.leaf_distances(states),{(0,1,0):1,(1,1,0):2})
        with self.assertRaises(UserError):art.leaf_distances({(0,0,0):art.NEW_LOG,(1,1,0):'minecraft:cherry_leaves'})
        for x in range(1,8):states[x,1,0]='minecraft:cherry_leaves'
        with self.assertRaises(UserError):art.leaf_distances(states)

    def test_gravel_pedestal_requires_a_bounded_real_stable_bottom(self):
        raw={(0,63,0):'minecraft:gravel',(0,62,0):'minecraft:sand',(0,61,0):'minecraft:stone',(0,64,0):'minecraft:air',(0,65,0):'minecraft:air'}
        g=bot.Garden(REGISTRY,raw.get,set(),set(),set());art.rooted_pot(g,(0,64,0),art.POTS[0])
        self.assertEqual(set(g.roots),{(0,63,0),(0,62,0),(0,61,0)})
        raw[0,61,0]='minecraft:water[level=0]';g=bot.Garden(REGISTRY,raw.get,set(),set(),set())
        with self.assertRaises(UserError):art.rooted_pot(g,(0,64,0),art.POTS[0])
        self.assertEqual(g.blocks,{})
        self.assertEqual(g.roots,{})


if __name__=='__main__':unittest.main()
