"""Source-level queued-reply identity regression; not a native Mixin acceptance test."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from control_room.common import REPO
from tools.living_world_upstream import reserve_allocation


class DeliveryIdentityTests(unittest.TestCase):
    def test_queued_reply_session_config_and_privacy_boundaries(self):
        jdk=Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
        javac=str(jdk/'javac.exe') if (jdk/'javac.exe').is_file() else shutil.which('javac')
        java=str(jdk/'java.exe') if (jdk/'java.exe').is_file() else shutil.which('java')
        if not javac or not java:
            self.skipTest('Java 21 compiler/runtime required; no download or game installation')
        reserve_allocation(Path(tempfile.gettempdir())/'awft-delivery-identity')
        with tempfile.TemporaryDirectory(prefix='awft-delivery-identity-') as directory:
            sources=[REPO/'compat/living-world/src/worldfortwo/living/DeliveryIdentity.java',
                     REPO/'proposals/living-world/mods/probes/DeliveryIdentitySelfTest.java']
            result=subprocess.run([javac,'--release','21','-encoding','UTF-8','-d',directory,*map(str,sources)],
                                  capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([java,'-Xmx64m','-cp',directory,'DeliveryIdentitySelfTest'],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('Delivery identity policy checks passed',result.stdout)


if __name__=='__main__':
    unittest.main()
