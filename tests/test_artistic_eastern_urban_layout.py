import unittest

from control_room.common import UserError
from tools.artistic_eastern_move_blueprint import cells,closed_vanilla_pairs
from tools.artistic_eastern_urban_layout import grow_parcels,largest_rectangle,rectangle,transaction_order
from tools.artistic_eastern_urban_custody import classify_current,pods_from_current


class EasternUrbanLayoutTests(unittest.TestCase):
    def test_growth_reaches_queued_neighbours_without_crossing_street(self):
        land={(x,z) for x in range(15) for z in range(9)};road={(7,z) for z in range(9)}
        seeds=[{'exact_seed':[2,4]},{'exact_seed':[12,4]}]
        parcels,left=grow_parcels(land,road,seeds,{(1,1):0})
        self.assertFalse(left)
        self.assertEqual(set.union(*parcels),land-road)
        self.assertFalse(parcels[0]&parcels[1]);self.assertIn((1,1),parcels[0])
        self.assertTrue(all(x<7 for x,z in parcels[0]))

    def test_room_rectangles_do_not_cover_holes_or_count_roads(self):
        land={(x,z) for x in range(12) for z in range(18)}-{(5,z) for z in range(9)}
        r=largest_rectangle(land,min_width=4,min_depth=5)
        self.assertIsNotNone(r);self.assertLessEqual(rectangle(r),land)
        self.assertFalse(rectangle(r)&{(5,z) for z in range(9)})

    def test_transfer_order_precedes_actual_occupied_destination(self):
        pods=[{'id':'a','records':[{'source_position':[0,65,0]}]},
              {'id':'b','records':[{'source_position':[20,65,0]}]}]
        transfers=[{'pod_id':'a','destination_support_bounds_xyz':[19,64,-1,21,67,1]},
                   {'pod_id':'b','destination_support_bounds_xyz':[39,64,-1,41,67,1]}]
        order,detail=transaction_order(transfers,pods,[{'position':[0,65,0]},{'position':[20,65,0]}])
        self.assertEqual(order,['b','a']);self.assertEqual(detail[0]['required_completed_move_ids'],['b'])
        with self.assertRaises(UserError):transaction_order(transfers,pods,[{'position':[20,65,0]},{'position':[40,65,0]}])
        transfers[1]['destination_support_bounds_xyz']=[-1,64,-1,1,67,1]
        with self.assertRaises(UserError):transaction_order(transfers,pods,[{'position':[0,65,0]},{'position':[20,65,0]}])

    def test_partial_door_and_bed_capsules_refuse_closure(self):
        door={(0,65,0):'minecraft:dark_oak_door[facing=north,half=lower]'}
        self.assertTrue(closed_vanilla_pairs(door,[-1,64,-1,1,66,1]))
        door[(0,66,0)]='minecraft:dark_oak_door[facing=north,half=upper]'
        self.assertFalse(closed_vanilla_pairs(door,[-1,64,-1,1,66,1]))
        bed={(0,65,0):'minecraft:blue_bed[facing=east,part=foot]',(1,65,0):'minecraft:blue_bed[facing=east,part=head]'}
        self.assertFalse(closed_vanilla_pairs(bed,[-1,64,-1,2,67,1]))
        self.assertTrue(closed_vanilla_pairs(bed,[-1,64,-1,0,67,1]))
        with self.assertRaises(UserError):cells([0,64,0,40,67,3])

    def test_current_be_and_unknown_origin_never_become_removable_shell(self):
        self.assertEqual(classify_current('minecraft:barrel','minecraft:barrel',True),'CURRENT_NATIVE_BE_REQUIRES_LOSSLESS_CUSTODY')
        self.assertEqual(classify_current(None,'minecraft:air',False),'UNOWNED_CURRENT_STATE_HOLD')
        self.assertEqual(classify_current('minecraft:air','minecraft:blue_bed',True,True),'PRIVATE_HUMAN_ANCHOR_RETAIN_IN_PLACE')

    def test_unknown_or_private_records_cannot_become_stock_pods(self):
        house={'id':'a','floor_y':64,'storeys':2}
        template={'saved_block':'minecraft:barrel','saved_BE_id':'minecraft:barrel','actual_full_typed_NBT_sha256':'a'*64}
        rows=[{**template,'position':[3,65,3],'main_outline_associations':['a'],'classification':'UNOWNED_OR_CHANGED_BE_RETAIN_IN_PLACE'},
              {**template,'position':[1296,65,-1250],'main_outline_associations':['a'],'classification':'PRIVATE_HUMAN_ANCHOR_RETAIN_IN_PLACE'},
              {**template,'position':[4,65,4],'main_outline_associations':['a'],'classification':'CURRENT_NATIVE_BE_REQUIRES_LOSSLESS_CUSTODY'}]
        pods,holds=pods_from_current(rows,[house])
        self.assertEqual(len(pods),1);self.assertEqual(len(holds),2)
        self.assertEqual(pods[0]['records'][0]['source_position'],[4,65,4])


if __name__=='__main__':unittest.main()
