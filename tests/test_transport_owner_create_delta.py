from pathlib import Path
import unittest
from unittest.mock import patch

from tools import transport_owner_create_delta as delta


class OwnerCreateDeltaTests(unittest.TestCase):
    before = b'[kinetics]\nmaxChainConveyorLength = 32\nmaxRotationSpeed = 256\n[other]\nenabled = true\n'
    after = before.replace(b'Length = 32', b'Length = 128')

    def check(self, before, after):
        with patch.object(delta, 'BEFORE_SHA', delta.sha(self.before)), patch.object(delta, 'AFTER_SHA', delta.sha(self.after)):
            delta.validate_pair(before, after)

    def test_exact_single_setting_passes(self):
        self.check(self.before, self.after)

    def test_extra_field_change_comment_change_or_unapproved_hash_refuses(self):
        for raw in (self.after.replace(b'256', b'512'), self.after+b'#extra\n', self.after.replace(b'128', b'129')):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.check(self.before, raw)

    def test_semantic_guard_remains_even_if_bad_hash_is_supplied_in_fixture(self):
        changed = self.after.replace(b'256', b'512')
        with patch.object(delta, 'BEFORE_SHA', delta.sha(self.before)), patch.object(delta, 'AFTER_SHA', delta.sha(changed)):
            with self.assertRaises(ValueError):
                delta.validate_pair(self.before, changed)

    def test_real_approved_hashes_and_native_guard_are_fixed(self):
        self.assertEqual(delta.BEFORE_SHA, '36216a05f3ed63106ba587c8c24ed6315385829e7f3dae695dcf545aba41a270')
        self.assertEqual(delta.AFTER_SHA, '240471ba821bd0f5208ea11960d79aacdfeb25a40c6a689a2d6518d689d890ac')
        self.assertIn(delta.RECEIPT_SHA, delta.JAVA_METHOD)
        self.assertIn('runtime_effective_value_observed",false', delta.JAVA_METHOD)

    def test_both_existing_source_contexts_adapt_without_touching_geometry_or_other_gates(self):
        root = Path(__file__).resolve().parents[1]
        producer = (root/'compat/control-bridge/proposals/mill-resume/prepare.py').read_text()
        native = (root/'compat/control-bridge/src/worldfortwo/bridge/ArtisticEngineeringSupport.java').read_text()
        if 'from tools.transport_owner_create_delta import binding as owner_create_binding' in producer:
            revised = producer
            with self.assertRaises(ValueError):
                delta.adapt_producer(producer)
        else:
            revised = delta.adapt_producer(producer)
        compile(revised, '<owner-delta-producer>', 'exec')
        self.assertIn("owner_create_delta=owner_create_binding(home,approved[0],value['sha256'])", revised)
        if 'private boolean approveOwnerChain128(' in native:
            native_after = native
            with self.assertRaises(ValueError):
                delta.adapt_native(native)
        else:
            native_after = delta.adapt_native(native)
        self.assertIn('hashes.add(new HashInput(p,binding.get("sha256").getAsString(),1024*1024))', native_after)
        self.assertIn('Actual current verified backup receipt required', native_after)
        self.assertIn('Complete R3 plus94 canonical geometry required', native_after)
        self.assertIn('Unused owner delta refused', native_after)

    def test_changed_source_context_cannot_silently_accept_a_broad_patch(self):
        with self.assertRaises(ValueError):
            delta.adapt_native('unrecognized source')
        with self.assertRaises(ValueError):
            delta.adapt_producer('unrecognized producer')


if __name__ == '__main__':
    unittest.main()
