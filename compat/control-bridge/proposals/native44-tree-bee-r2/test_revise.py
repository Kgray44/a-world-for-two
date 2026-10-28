import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('bee_additive_revision',Path(__file__).with_name('revise.py'))
revision=importlib.util.module_from_spec(spec);spec.loader.exec_module(revision)


class RevisionCustodyTests(unittest.TestCase):
    def test_only_the_two_reviewed_guard_controller_files_change(self):
        old,new=revision.source_pair()
        self.assertEqual({k for k in old if old[k]!=new[k]},{'TreeGrowthScope.java','NativeTreeGrowthSupport.java'})
        for name,expected in revision.PINS.items():self.assertEqual(hashlib.sha256((revision.OLD/name).read_bytes()).hexdigest(),expected)

    def test_changed_frozen_source_refuses_before_output_writer(self):
        pins=dict(revision.PINS);pins['TreeBeeAudit.java']='0'*64
        with patch.object(revision,'PINS',pins),self.assertRaises(ValueError):revision.source_pair()

    def test_missing_or_duplicate_integration_anchor_is_not_silently_applied(self):
        with self.assertRaises(ValueError):revision.replace('unrelated source','expected source','new')
        with self.assertRaises(ValueError):revision.replace('one one','one','new')

    def test_existing_source_receipt_folder_is_never_overwritten(self):
        with self.assertRaises(ValueError):revision.materialize('D:/A World for Two/staging/native44-tree-bee-compile-20261028T0016Z',guard=False)


if __name__=='__main__':unittest.main()
