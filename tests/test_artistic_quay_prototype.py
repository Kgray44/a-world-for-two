"""Focused admission boundaries, not fabricated native or artistic acceptance."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from control_room.common import UserError, digest
from tools.artistic_quay_prototype import approach_columns, apron_clearance, exact_preimage, fresh_proof, pending_member_name


class QuayPrototypeAdmissionTests(unittest.TestCase):
    def test_fixed_member_binding_uses_the_real_frozen_filename(self):
        self.assertEqual(pending_member_name('fixed'),'fixed-ornament-PENDING-NATIVE.json')
        self.assertEqual(pending_member_name('tavern'),'tavern-PENDING-NATIVE.json')

    def test_only_exact_dry_ordinary_apron_cover_is_clearable(self):
        self.assertFalse(apron_clearance('minecraft:air'))
        self.assertTrue(apron_clearance('supplementaries:barnacles[down=true,waterlogged=false]'))
        self.assertTrue(apron_clearance('regions_unexplored:grass_sprouts'))
        for value in ('supplementaries:barnacles[waterlogged=true]','minecraft:dead_bubble_coral[waterlogged=false]','minecraft:oak_log[axis=y]'):
            with self.assertRaises(UserError):apron_clearance(value)

    def test_threshold_external_natural_apron_tracks_actual_stair_heading(self):
        q=(12,64,-80)
        north=approach_columns({q:'minecraft:spruce_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]'},q)
        self.assertEqual(north,{(x,z) for x in (11,12,13) for z in (-81,-82)})
        south=approach_columns({q:'minecraft:spruce_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]'},q)
        self.assertEqual(south,{(x,z) for x in (11,12,13) for z in (-79,-78)})
        self.assertNotIn((12,-80),north|south)

    def test_a_top_stair_cannot_silently_change_the_outdoor_walking_level(self):
        q=(12,64,-80)
        with self.assertRaises(UserError):
            approach_columns({q:'minecraft:spruce_stairs[facing=south,half=top]'},q)

    def test_preimage_checks_block_entity_custody_even_when_identity_matches(self):
        class Saved:
            protected={(1,64,2)}
            def state(self,q):return 'minecraft:air'
        with self.assertRaises(UserError):exact_preimage(Saved(),{(1,64,2):'minecraft:air'})
        Saved.protected=set()
        with self.assertRaises(UserError):exact_preimage(Saved(),{(1,64,2):'minecraft:stone'})

    def receipt(self,folder,**changes):
        now=datetime.now(timezone.utc)
        data={'operation':'verify','plan_sha256':'a'*64,'blocks':9,'failures':0,
              'status':'verified actual block identities, orientation, block entities and supplied inventories',
              'started':(now-timedelta(seconds=3)).isoformat(),'finished':(now-timedelta(seconds=1)).isoformat(),
              'cleanup_required':False,'temporary_tickets_remaining':0,'pending_shared_chunk_futures':0}
        data.update(changes);p=Path(folder)/'synthetic-native-schema.json'
        p.write_text(json.dumps(data));p.with_name(p.name+'.complete').write_text(digest(p))
        return p,now

    def test_actual_schema_has_no_invented_cleanup_passed_field(self):
        with tempfile.TemporaryDirectory() as t:
            p,now=self.receipt(t)
            proof,_=fresh_proof(p,'a'*64,9,now=now)
            self.assertNotIn('cleanup_passed',proof)

    def test_partial_cleanup_missing_schema_and_wrong_coverage_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            for change in ({'pending_shared_chunk_futures':1},{'cleanup_required':True},
                           {'ticket_cleanup_error':'retained'},{'blocks':8},{'pending_shared_chunk_futures':None}):
                p,now=self.receipt(t,**change)
                with self.assertRaises(UserError):fresh_proof(p,'a'*64,9,now=now)

    def test_stale_or_unmarked_receipt_does_not_admit_a_prototype(self):
        with tempfile.TemporaryDirectory() as t:
            p,now=self.receipt(t)
            with self.assertRaises(UserError):fresh_proof(p,'a'*64,9,now=now+timedelta(minutes=6))
            p.with_name(p.name+'.complete').write_text('b'*64)
            with self.assertRaises(UserError):fresh_proof(p,'a'*64,9,now=now)


if __name__=='__main__':unittest.main()
