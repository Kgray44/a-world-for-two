"""The photographed Cooper failure: a low neighbour hides only the low wall."""
import unittest

from tools.artistic_eastern_attached_clerestories import exposed_casements


class AttachedUpperCasements(unittest.TestCase):
    def fixture(self):
        source={'origin':[0,64,0],'masses':[{'bounds_xz':[0,0,11,4]}],
            'roof_sections':[{'mass':0,'base':8}],
            'width_review':{'floors':[{'mass':0,'floor':0,'feet_y':65},{'mass':0,'floor':1,'feet_y':69}]}}
        own={(x,y,4):('minecraft:stripped_dark_oak_log[axis=y]' if x in(0,4,8,11)
            else 'minecraft:brown_terracotta') for x in range(12)for y in range(65,72)}
        own.update({(x,72,4):'chipped:reinforced_dark_oak_log[axis=x]' for x in range(12)})
        roof={(x,69,5):'minecraft:dark_oak_stairs[facing=south]' for x in range(12)}
        columns={(x,5) for x in range(12)}
        return source,own,roof,columns

    def test_upper_window_moves_above_actual_roof_and_keeps_party_wall(self):
        source,own,roof,columns=self.fixture()
        changes,details=exposed_casements(source,own,roof,columns,set())
        panes={q:v for q,v in changes.items() if 'four_window' in v}
        self.assertTrue(panes)
        self.assertEqual({q[1] for q in panes},{70,71})
        self.assertFalse(set(changes)&set(roof))
        self.assertFalse(any(q[1]<70 for q in changes))
        self.assertTrue(all(r['retained_lower_party_wall_and_adjacent_roof'] for r in details))
        self.assertTrue(any('shutter' in v for v in changes.values()))

    def test_taller_neighbour_remains_a_party_wall(self):
        source,own,roof,columns=self.fixture()
        roof.update({(x,75,5):'minecraft:brown_terracotta' for x in range(12)})
        self.assertEqual(exposed_casements(source,own,roof,columns,set()),({},[]))

    def test_real_body_clearance_cannot_become_a_new_projection(self):
        source,own,roof,columns=self.fixture()
        body={(x,y,5) for x in range(12) for y in(70,71)}
        self.assertEqual(exposed_casements(source,own,roof,columns,body),({},[]))


if __name__=='__main__':unittest.main()
