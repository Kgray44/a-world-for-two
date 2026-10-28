import unittest
from control_room.common import UserError
from tools.artistic_north_bank_east_connector import checked_connector

class Threshold(unittest.TestCase):
    def field(self):return {(x,y,z):'minecraft:grass_block[snowy=false]' if y==63 else 'minecraft:short_grass' if y==64 else 'minecraft:air' for x in (1289,1290) for y in (63,64,65) for z in (-1241,-1240,-1239)}
    def test_only_the_eighteen_natural_gap_cells_change(self):
        delta=checked_connector(self.field(),{});self.assertEqual(len(delta),18);self.assertEqual(sum(s=='minecraft:air' for s in delta.values()),12)
    def test_old_authored_solid_is_never_replayed(self):
        with self.assertRaises(UserError):checked_connector(self.field(),{(1289,63,-1240):'minecraft:stone_bricks'})
    def test_existing_air_expectation_stays_air(self):
        delta=checked_connector(self.field(),{(1289,64,-1240):'minecraft:air'});self.assertEqual(delta[1289,64,-1240],'minecraft:air')
    def test_authored_air_cannot_become_a_paver(self):
        with self.assertRaises(UserError):checked_connector(self.field(),{(1289,63,-1240):'minecraft:air'})
    def test_water_cannot_be_treated_as_an_unfinished_path(self):
        field=self.field();field[1289,63,-1240]='minecraft:water[level=0]'
        with self.assertRaises(UserError):checked_connector(field,{})

if __name__=='__main__':unittest.main()
