"""Actual archived dry-shape refusal boundaries; no native receipt is fabricated."""
from copy import deepcopy
import unittest
from control_room.common import UserError
from tools.artistic_fountain_commission_47 import require_actual_dry


class Fountain47DryShapeTests(unittest.TestCase):
    def test_a_wet_or_prospective_manifest_is_rejected_before_geometry_or_native_io(self):
        for value in ({},{'actual_dry_checkpoint':False},{'actual_dry_checkpoint':True,'format':'prospective'}):
            with self.subTest(value=value),self.assertRaises(UserError):require_actual_dry(value,{}, {}, {'id':'fixture','sha256':'0'*64})

    def test_new_source_keeps_previous_build_and_function_acceptance_separate(self):
        # No request/write function is called: an old manifest cannot inherit47.
        manifest={'format':'awft-r5-cohesive-guardian-fountain:1','actual_dry_checkpoint':True,
                  'previous_actual_R5_geometry_sha256':'wrong','checkpoint_id':'fixture','checkpoint_sha256':'0'*64,
                  'files':{'actual-dry-native-BEFORE.json':{}}}
        with self.assertRaises(UserError):require_actual_dry(manifest,{}, {}, {'id':'fixture','sha256':'0'*64})
