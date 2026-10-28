"""Pure Java admission checks; no Minecraft runtime or multiplayer claims."""
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest

from control_room.common import REPO
from tools.living_world_upstream import reserve_allocation


class AmbientBudgetJavaTests(unittest.TestCase):
    def test_present_observer_admission(self):
        jdk = Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
        javac = str(jdk / 'javac.exe') if (jdk / 'javac.exe').is_file() else shutil.which('javac')
        java = str(jdk / 'java.exe') if (jdk / 'java.exe').is_file() else shutil.which('java')
        if not javac or not java:
            self.skipTest('Existing Java 21 compiler required; no installation performed')
        reserve_allocation(Path(tempfile.gettempdir()) / 'awft-ambient-budget-probe')
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        with tempfile.TemporaryDirectory(prefix='awft-ambient-budget-') as directory:
            sources = [REPO / 'compat/living-world/src/worldfortwo/living/AmbientBudget.java',
                       REPO / 'proposals/living-world/mods/probes/AmbientBudgetSelfTest.java']
            compile_result = subprocess.run([javac, '--release', '21', '-encoding', 'UTF-8',
                '-d', directory, *map(str, sources)], capture_output=True, text=True, timeout=30, creationflags=flags)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            run = subprocess.run([java, '-Xmx64m', '-cp', directory, 'AmbientBudgetSelfTest'],
                capture_output=True, text=True, timeout=15, creationflags=flags)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('AmbientBudget present-observer rate', run.stdout)


if __name__ == '__main__':
    unittest.main()
