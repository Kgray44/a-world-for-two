import unittest
from control_room.common import UserError
from tools.artistic_bridge_topside_custody import BOXES,exact_glues,enclosed


class RetainedGlueBoundaryTests(unittest.TestCase):
    def rows(self):
        return [{'uuid':label,'bounds':list(box),'entity_id':'create:super_glue'} for label,box in BOXES.items()]
    def test_full_voxel_must_fit_the_existing_exclusive_max_box(self):
        box=BOXES['north']
        self.assertTrue(enclosed((1198,73,-1144),box))
        for q in ((1199,73,-1144),(1198,74,-1144),(1198,73,-1143)):
            self.assertFalse(enclosed(q,box))
    def test_refuses_historical_taller_box_or_unaccounted_glue(self):
        rows=self.rows();rows[0]['bounds'][4]=75.
        with self.assertRaises(UserError):exact_glues(rows)
        rows=self.rows();rows.append(dict(rows[0],uuid='extra'))
        with self.assertRaises(UserError):exact_glues(rows)
    def test_exact_current_distinct_boxes_are_matched_without_old_uuid_assumption(self):
        rows=self.rows();rows.reverse()
        self.assertEqual(exact_glues(rows)['north']['uuid'],'north')
        rows[0]['uuid']=rows[1]['uuid']
        with self.assertRaises(UserError):exact_glues(rows)
