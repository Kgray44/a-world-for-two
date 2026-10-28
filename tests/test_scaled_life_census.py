import unittest
import uuid
from control_room.common import UserError
from tools.habitat_life import census as legacy_census
from tools.native_scaled_life import census


class EmptySavedSnapshot:
    prefix='owned-world/region/'
    files={}


def members(count):
    return [{'uuid':str(uuid.UUID(int=i+1)),'member_tag':'fixture_'+str(i),'feet':[i*32+.5,65,-.5]}for i in range(count)]


class ScaledLifeCensusTests(unittest.TestCase):
    def test_64_requested_identities_and_all64_habitat_tiles_are_retained(self):
        ids,tiles=census(EmptySavedSnapshot(),members(64),'fixture-checkpoint','fixture-recipe')
        self.assertEqual(64,len(ids['members']))
        self.assertTrue(ids['all_requested_UUID_absent'])
        self.assertEqual(64,len(tiles['tiles']))
        self.assertTrue(all(row['saved_entity_count']==0 for row in tiles['tiles']))

    def test_65_or_duplicate_requested_ids_refuse(self):
        with self.assertRaises(UserError):census(EmptySavedSnapshot(),members(65),'c','r')
        duplicate=members(2);duplicate[1]['uuid']=duplicate[0]['uuid']
        with self.assertRaises(UserError):census(EmptySavedSnapshot(),duplicate,'c','r')

    def test_legacy_16_member_boundary_is_not_silently_upgraded(self):
        with self.assertRaises(UserError):legacy_census(EmptySavedSnapshot(),members(64),'c','r')


if __name__=='__main__':unittest.main()
