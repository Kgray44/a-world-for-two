import unittest
from control_room.common import UserError
from tools.artistic_south_forest48 import unperformed


class SouthForest48Tests(unittest.TestCase):
    def setUp(self):
        self.plots=[{'id':f'south47-{n:02}'}for n in range(1,26)if n!=5]
        self.outcomes=[{'id':f'south47-{n:02}'}for n in (1,2,3,4,6,7,8,9)]

    def test_all_attempted_outcomes_stay_excluded_regardless_of_success(self):
        rows=unperformed(self.plots,self.outcomes)
        self.assertEqual([f'south47-{n:02}'for n in range(10,26)],[r['id']for r in rows])

    def test_missing_failed_record_cannot_enable_a_reroll(self):
        with self.assertRaises(UserError):unperformed(self.plots,self.outcomes[:-1])

    def test_new_native_attempt_invalidates_old_source_selection(self):
        with self.assertRaises(UserError):unperformed(self.plots,self.outcomes+[{'id':'south47-10'}])


if __name__=='__main__':unittest.main()
