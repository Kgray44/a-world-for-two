import hashlib,json,tempfile,unittest,warnings,zipfile
from pathlib import Path
from unittest.mock import patch
import nbtlib
from control_room.common import UserError
from tools.native_relocation_request import LAYOUT_SHA,class_hash,native_proof,owner_review,unchanged_saved_capture


class NativeRelocationRequestTests(unittest.TestCase):
    def test_city_map_review_cannot_be_inferred_or_transferred_from_another_plan(self):
        row={'format':'awft-owner-city-plan-review:1','approved':True,'eastern_layout_sha256':LAYOUT_SHA,'allowed_operations':['pippin-native-relocation-prototype']}
        self.assertEqual(owner_review(row),row)
        for replacement in ({'approved':False},{'approved':'true'},{'eastern_layout_sha256':'a'*64},{'allowed_operations':['entire-city']}):
            with self.assertRaises(UserError):owner_review({**row,**replacement})
        with self.assertRaises(UserError):owner_review({})

    def test_native_proof_requires_exact_marked_plan_and_clean_status(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);p=home/'dashboard/settlement/settlement-result-test.json';p.parent.mkdir(parents=True)
            row={'operation':'verify','plan_sha256':'a'*64,'blocks':320,'failures':0,'cleanup_required':False,'temporary_tickets_remaining':0,'pending_shared_chunk_futures':0,
                 'status':'verified actual block identities, orientation, block entities and supplied inventories'}
            def write(r):
                p.write_text(json.dumps(r));sha=hashlib.sha256(p.read_bytes()).hexdigest();p.with_name(p.name+'.complete').write_text(sha);return sha
            sha=write(row);self.assertEqual(native_proof(home,p,sha,'a'*64,320)['sha256'],sha)
            for change in ({'status':'verification failed; inspect differences'},{'temporary_tickets_remaining':1},{'pending_shared_chunk_futures':1},{'ticket_cleanup_error':'retained'},{'plan_sha256':'b'*64},{'failures':1}):
                sha=write({**row,**change})
                with self.assertRaises(UserError):native_proof(home,p,sha,'a'*64,320)
            sha=write(row);p.with_name(p.name+'.complete').write_text('b'*64)
            with self.assertRaises(UserError):native_proof(home,p,sha,'a'*64,320)

    def test_duplicate_named_class_cannot_pin_the_wrong_archive_member(self):
        with tempfile.TemporaryDirectory() as temp:
            jar=Path(temp)/'test.jar'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                with zipfile.ZipFile(jar,'w') as z:z.writestr('demo/Entry.class',b'first');z.writestr('demo/Entry.class',b'second')
            with self.assertRaises(UserError):class_hash(jar,'demo.Entry')

    def test_fresh_archive_is_read_and_typed_inventory_width_changes_are_held(self):
        source={(1236+x,64,-1194):'minecraft:stone' for x in range(7)}
        destination={(1223,64,-1194):'minecraft:air'};supports={(1223,63,-1194):'minecraft:stone'}
        tags=[nbtlib.Compound({'x':nbtlib.Int(x),'y':nbtlib.Int(y),'z':nbtlib.Int(z),
            'id':nbtlib.String('test:container'),'Items':nbtlib.List[nbtlib.Compound]([
                nbtlib.Compound({'Slot':nbtlib.Byte(0),'id':nbtlib.String('minecraft:paper'),'count':nbtlib.Int(1)})])})
            for x,y,z in source]
        rows=[{'pos':list(q),'nbt':tag.snbt()} for q,tag in zip(source,tags)]
        class Saved:
            def __init__(self):
                self.regions={(2,-3):b'authenticated test region'};self.protected=set(source);self.sources=[];self.read=[];self.full=[];self.closed=False
            def chunk(self,x,z):self.full.append((x,z))
            def state(self,q):self.read.append(q);return {**source,**destination,**supports}[q]
            def close(self):self.closed=True
        saved=Saved();receipt={'id':'current-test','sha256':'c'*64}
        with patch('tools.native_relocation_request.BackupWorld',return_value=saved),patch('tools.native_relocation_request.decoded_chunk',return_value={'block_entities':tags}),patch('tools.native_relocation_request.reader_budget',return_value={'owned_reader_rss_bytes':1024}):
            result=unchanged_saved_capture(Path('.'),receipt,{},source,destination,supports,rows)
        self.assertTrue(saved.closed);self.assertEqual(set(saved.read),set(source)|set(destination)|set(supports));self.assertEqual(len(saved.full),12)
        self.assertTrue(result['seven_full_typed_tags_unchanged']);self.assertFalse(result['current_native_entity_readiness_proved'])
        # Same numerical slot value with a different actual NBT width is NOT
        # conservation: this must stop before any prospective plan is emitted.
        changed=[nbtlib.parse_nbt(tag.snbt()) for tag in tags];changed[0]['Items'][0]['Slot']=nbtlib.Int(0)
        with patch('tools.native_relocation_request.BackupWorld',return_value=Saved()),patch('tools.native_relocation_request.decoded_chunk',return_value={'block_entities':changed}),patch('tools.native_relocation_request.reader_budget',return_value={'owned_reader_rss_bytes':1024}):
            with self.assertRaisesRegex(UserError,'full typed'):unchanged_saved_capture(Path('.'),receipt,{},source,destination,supports,rows)
        changed_saved=Saved();changed_saved.state=lambda q:'minecraft:gold_block'
        with patch('tools.native_relocation_request.BackupWorld',return_value=changed_saved),patch('tools.native_relocation_request.reader_budget',return_value={'owned_reader_rss_bytes':1024}):
            with self.assertRaisesRegex(UserError,'state changed'):unchanged_saved_capture(Path('.'),receipt,{},source,destination,supports,rows)
        self.assertTrue(changed_saved.closed)


if __name__=='__main__':unittest.main()
