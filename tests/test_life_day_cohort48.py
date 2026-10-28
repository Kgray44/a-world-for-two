from copy import deepcopy
import unittest

from control_room.common import UserError
from tools.artistic_life_day_cohort48 import HELD, daytime_members, habitat_bounds


class DayCohort48Tests(unittest.TestCase):
    def setUp(self):
        self.day=[{'uuid':'uuid-'+str(n),'entity':'species:'+str(n),'feet':[n,64,0],
                   'source_group_id':'site-'+str(n),'preimage':[[n,63,0,'minecraft:grass_block']]}for n in range(7)]
        self.recipe={'members':self.day[:2]+[{'uuid':HELD,'entity':'naturalist:firefly'}]+self.day[2:]}

    def test_split_changes_no_day_identity_site_or_field(self):
        before=deepcopy(self.recipe);actual=daytime_members(self.recipe)
        self.assertEqual(self.day,actual);self.assertEqual(before,self.recipe)
        actual[0]['feet'][0]=999
        self.assertEqual(before,self.recipe)

    def test_missing_or_replaced_held_actor_refuses(self):
        for mutation in ('missing','identity','type'):
            r=deepcopy(self.recipe)
            if mutation=='missing':r['members'].pop(2)
            elif mutation=='identity':r['members'][2]['uuid']='new-random-id'
            else:r['members'][2]['entity']='minecraft:bat'
            with self.assertRaises(UserError):daytime_members(r)

    def test_another_nocturnal_firefly_cannot_enter_day_set(self):
        r=deepcopy(self.recipe);r['members'][0]['entity']='naturalist:firefly'
        with self.assertRaises(UserError):daytime_members(r)

    def test_native_bounds_are_actual_xz_minima_and_maxima(self):
        self.assertEqual([1101,-1283,1294,-781],habitat_bounds({(1294,74,-1283):'a',(1101,169,-781):'b'}))
        for field in ({},{(0,1,0):'a',(513,1,0):'b'},{(True,1,0):'a'}):
            with self.assertRaises(UserError):habitat_bounds(field)


if __name__=='__main__':unittest.main()
