"""Real JVM checks of the adapter's pure core; this is not gameplay evidence."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from control_room.common import REPO
from tools.living_world_upstream import reserve_allocation


class LivingWorldJavaTests(unittest.TestCase):
    def test_java_character_configuration_boundaries(self):
        jdk = Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
        javac = str(jdk / 'javac.exe') if (jdk / 'javac.exe').is_file() else shutil.which('javac')
        java = str(jdk / 'java.exe') if (jdk / 'java.exe').is_file() else shutil.which('java')
        gson = Path(os.environ.get('AWFT_GSON_JAR', r'D:\A World for Two\server\libraries\com\google\code\gson\gson\2.10.1\gson-2.10.1.jar'))
        if not javac or not java or not gson.is_file():
            self.skipTest('Existing Java 21 compiler and Gson compiler input required; no downloads performed')
        reserve_allocation(Path(tempfile.gettempdir()) / 'awft-java-probe')
        with tempfile.TemporaryDirectory(prefix='awft-java-probe-') as directory:
            classes = Path(directory)
            sources = [REPO / 'compat/living-world/src/worldfortwo/living/WorldCharacters.java',
                       REPO / 'proposals/living-world/mods/probes/WorldCharactersSelfTest.java']
            result = subprocess.run([javac, '--release', '21', '-encoding', 'UTF-8', '-cp', str(gson),
                                     '-d', str(classes), *map(str, sources)], capture_output=True, text=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            result = subprocess.run([java, '-Xmx64m', '-cp', str(classes) + os.pathsep + str(gson),
                                     'WorldCharactersSelfTest'], capture_output=True, text=True, timeout=15)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn('WorldCharacters source checks passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
