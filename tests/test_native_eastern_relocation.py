import copy,hashlib,unittest
from pathlib import Path
from control_room.common import UserError
from tools.native_eastern_relocation import checked_row,transaction,PIPPIN
from tools.artistic_eastern_urban_custody import CHECKPOINT_SHA


class EasternRelocationTests(unittest.TestCase):
    def row(self):return {'id':'test/room:0','source_bounds_xyz':[1236,64,-1194,1243,67,-1185],
        'destination_bounds_xyz':[1223,64,-1194,1230,67,-1185],'translation_xyz':[-13,0,0],'cells':320,'supported':True,'holds':[]}
    def test_cardinal_identical_closure_and_explicit_hold(self):
        row=self.row();self.assertIs(checked_row({'capsules':[row]},row['id']),row)
        for key,value in (('translation_xyz',[0,0,0]),('destination_bounds_xyz',[1223,64,-1194,1231,67,-1185]),('source_bounds_xyz',[1236.5,64,-1194,1243,67,-1185]),('supported',False)):
            altered={**row,key:value}
            with self.assertRaises(UserError):checked_row({'capsules':[altered]},row['id'])
        with self.assertRaises(UserError):checked_row({'capsules':[row,row]},row['id'])
        with self.assertRaises(UserError):checked_row({'capsules':[row]},'not/approved:0')
    def test_pippin_legacy_transaction_cannot_be_reset_by_new_catalogue(self):
        home=Path('D:/A World for Two/staging/world-tests/fixture').resolve()
        old=hashlib.sha256((str(home)+'|'+CHECKPOINT_SHA+'|PIPPIN320|-13,0,0').encode()).hexdigest()
        self.assertEqual(transaction(home,PIPPIN,[-13,0,0]),old)
        self.assertNotEqual(transaction(home,'rose-reach/tea:room:1',[-69,-4,26]),old)


if __name__=='__main__':unittest.main()
