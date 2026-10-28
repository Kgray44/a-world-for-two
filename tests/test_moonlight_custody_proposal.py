from pathlib import Path
import hashlib
import unittest

from control_room.common import UserError
from tools.artistic_moonlight_custody_proposal import BASE,transform


class MoonlightCustodyBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[1]
        folder=root/'compat/proposals/resource-custody-moonlight49'
        cls.base=(folder/'LithostitchedSeedgenResources48-base.java.txt').read_text()
        cls.proposed=(folder/'LithostitchedSeedgenResources.java').read_text()

    def test_complete_proposal_derives_only_from_exact_owned_base(self):
        self.assertEqual(BASE,hashlib.sha256(self.base.encode()).hexdigest())
        self.assertEqual(self.proposed,transform(self.base))
        with self.assertRaises(UserError):transform('unknown resource implementation')

    def test_effective_pack_order_stacks_and_fingerprint_protocol_unchanged(self):
        start='    public static Attestation capture('
        end='    /** The native listing'
        old=self.base[self.base.index(start):self.base.index(end)]
        new=self.proposed[self.proposed.index(start):self.proposed.index(end)]
        new=new.replace('        for(var view:out.cachedViews)view.unchanged();\n','')
        self.assertEqual(old,new)

    def test_selected_absence_and_all_original_traversal_bounds_unchanged(self):
        start='    /** A null native lookup'
        old=self.base[self.base.index(start):self.base.index('    private static BasicFileAttributes attributes')]
        new=self.proposed[self.proposed.index(start):self.proposed.index('    /** Strict folder bytes')]
        self.assertEqual(old,new)
        for line in self.base.splitlines():
            if 'private static final int MAX_'in line or 'private static final long MAX_'in line:
                self.assertIn(line,self.proposed)


if __name__=='__main__':unittest.main()
