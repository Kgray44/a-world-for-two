"""Focused proposed receipt contract checks, never actual backup acceptance."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
from tools import native_scaled_life as module


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        parent=ROOT/'test-fixtures';parent.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=parent)
        self.home=Path(self.tmp.name).resolve()
        self.assertTrue(self.home.is_relative_to(ROOT.resolve()))
        self.addCleanup(self.tmp.cleanup)
        self.canonical=self.home/module.CANONICAL_CHECKPOINT
        self.canonical.parent.mkdir(parents=True)
        self.legacy={'verified':True,'id':module.CANONICAL_CUSTODY_ID,'sha256':module.CANONICAL_CUSTODY_SHA}
        self.canonical.write_text(json.dumps(self.legacy),encoding='utf8')
        raw=self.canonical.read_bytes()
        self.retained={'format':module.LIFE_CHECKPOINT_FORMAT,'verified':True,'id':'20261029T140000Z-abc123','sha256':'a'*64,
                       'source_custody':{'path':module.CANONICAL_CHECKPOINT,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}
        self.life=self.home/module.LIFE_CHECKPOINT
        self.write_retained(self.retained)

    def write_retained(self,value):
        self.life.write_text(json.dumps(value),encoding='utf8')

    def test_legacy_default_and_explicit_canonical_do_not_require_new_format(self):
        self.assertEqual(module.checkpoint_input(self.home,{})[1],self.legacy)
        self.assertEqual(module.checkpoint_input(self.home,{'checkpoint_receipt':module.CANONICAL_CHECKPOINT})[1],self.legacy)
        self.assertEqual(self.canonical.read_text(),json.dumps(self.legacy))

    def test_explicit_retained_selects_actual_new_identity_and_keeps_custody(self):
        path,value=module.checkpoint_input(self.home,{'checkpoint_receipt':module.LIFE_CHECKPOINT})
        self.assertEqual(path,self.life)
        self.assertEqual(value['id'],'20261029T140000Z-abc123')
        self.assertEqual(value['sha256'],'a'*64)
        self.assertEqual(json.loads(self.canonical.read_text()),self.legacy)
        self.assertEqual(module.checkpoint_input(self.home,{})[0],self.canonical)

    def test_arbitrary_absolute_traversal_alias_and_null_receipts_refuse(self):
        for value in ('dashboard/settlement/other.json','../backup-receipt.json',str(self.life),
                      'dashboard/settlement/./life-backup-receipt.json','dashboard\\settlement\\life-backup-receipt.json',None):
            with self.subTest(value=value),self.assertRaises(module.UserError):
                module.checkpoint_input(self.home,{'checkpoint_receipt':value})

    def test_unverified_malformed_retained_and_changed_custody_refuse(self):
        for key,value in [('verified',False),('verified','true'),('id','wrong'),('sha256','not-a-sha'),('format','wrong')]:
            bad=deepcopy(self.retained);bad[key]=value;self.write_retained(bad)
            with self.subTest(key=key,value=value),self.assertRaises(module.UserError):
                module.checkpoint_input(self.home,{'checkpoint_receipt':module.LIFE_CHECKPOINT})
        for key,value in [('path',module.LIFE_CHECKPOINT),('sha256','b'*64),('bytes',True),('bytes',1.5),('bytes',4097)]:
            bad=deepcopy(self.retained);bad['source_custody'][key]=value;self.write_retained(bad)
            with self.subTest(custody=key,value=value),self.assertRaises(module.UserError):
                module.checkpoint_input(self.home,{'checkpoint_receipt':module.LIFE_CHECKPOINT})
        self.write_retained(self.retained)
        self.canonical.write_text(json.dumps(dict(self.legacy,verified=False)),encoding='utf8')
        with self.assertRaises(module.UserError):
            module.checkpoint_input(self.home,{'checkpoint_receipt':module.LIFE_CHECKPOINT})

    def test_rehashed_custody_with_wrong6ad_identity_refuses(self):
        self.canonical.write_text(json.dumps(dict(self.legacy,id='20261029T140000Z-abc123')),encoding='utf8')
        raw=self.canonical.read_bytes();self.retained['source_custody'].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        self.write_retained(self.retained)
        with self.assertRaises(module.UserError):
            module.checkpoint_input(self.home,{'checkpoint_receipt':module.LIFE_CHECKPOINT})


if __name__=='__main__':unittest.main(verbosity=2)
