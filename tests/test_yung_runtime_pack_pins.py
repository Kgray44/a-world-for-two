"""Portable source/provenance checks; the exact-JAR executable probe is separate."""
import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT=Path(__file__).resolve().parents[1]
PROPOSAL=ROOT/'compat/control-bridge/proposals/resource-custody-yungs47'
ACTIVE=ROOT/'compat/control-bridge/src/worldfortwo/bridge'


class YungRuntimePackPins(unittest.TestCase):
    def test_exact_runtime_version_and_size_cover_the_canonical_selected_provider(self):
        lock=json.loads((ROOT/'catalog/lock.json').read_text(encoding='utf-8'))
        selected=[entry for entry in lock['mods'] if entry.get('project_id')=='Ua7DFN59']
        self.assertEqual(len(selected),1)
        helper=(ACTIVE/'YungLocatePackCustody.java').read_text(encoding='utf-8')
        version=re.search(r'getVersion\(\)\.toString\(\)\.equals\("([^\"]+)"\)',helper).group(1)
        size=int(re.search(r'before\.size\(\)!=(\d+)',helper).group(1))
        self.assertEqual(version,selected[0]['version'])
        self.assertEqual(size,selected[0]['size'])
        self.assertEqual(selected[0]['filename'],'YungsApi-'+version+'.jar')

    def test_active_source_matches_the_reviewed_exact_api_probe_inputs(self):
        seal=json.loads((PROPOSAL/'source-freeze.json').read_text(encoding='utf-8'))
        self.assertTrue(seal['offline_actual_api_probe_passed'])
        self.assertFalse(seal['native_full_loader_acceptance'])
        self.assertFalse(seal['strict_fingerprint_or_sharing_accepted'])
        for name in ('YungLocatePackCustody.java',):
            with self.subTest(name=name):
                actual=(ACTIVE/name).read_bytes()
                self.assertEqual(hashlib.sha256(actual).hexdigest(),seal['files'][name]['sha256'])
                self.assertEqual(actual,(PROPOSAL/name).read_bytes())

        # The current resource adapter composes the retained YUNG provider with
        # the separately reviewed Moonlight cache adapter. Both literal frozen
        # inputs keep their own API-probe custody; LF is Git's active-source form.
        moonlight=ROOT/'compat/proposals/resource-custody-moonlight49'
        current=json.loads((moonlight/'final-integration-custody.json').read_text(encoding='utf-8'))
        self.assertEqual(current['frozen_base_sha256'],seal['files']['LithostitchedSeedgenResources.java']['sha256'])
        self.assertEqual(current['actual_api_receipt']['compile_exit'],0)
        self.assertEqual(current['actual_api_receipt']['probe_exit'],0)
        for name in ('LithostitchedSeedgenResources.java','MoonlightCachePackCustody.java'):
            with self.subTest(composed=name):
                raw=(moonlight/name).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),current['final_sources'][name])
                self.assertEqual((ACTIVE/name).read_bytes(),raw.replace(b'\r\n',b'\n'))


if __name__=='__main__':
    unittest.main()
