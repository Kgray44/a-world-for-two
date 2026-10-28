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
    def test_global_provider_policy_callback_without_game_or_network(self):
        from control_room.common import digest
        from tools.build_living_world import PINS
        jdk=Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
        smart=REPO/'.local/living-world/smartvillagers-neoforge-1.21.1-2.0.0.jar'
        libraries=Path(r'D:\A World for Two\server\libraries')
        jars=[libraries/'com/google/code/gson/gson/2.10.1/gson-2.10.1.jar',
              libraries/'com/electronwill/night-config/core/3.8.3/core-3.8.3.jar',
              libraries/'net/fabricmc/sponge-mixin/0.16.4+mixin.0.8.7/sponge-mixin-0.16.4+mixin.0.8.7.jar',smart]
        if not (jdk/'javac.exe').is_file() or not all(p.is_file() for p in jars):
            self.skipTest('Existing pinned upstream compiler inputs required; no download or game installation')
        self.assertEqual(digest(smart),PINS[smart.name])
        reserve_allocation(Path(tempfile.gettempdir())/'awft-provider-probe')
        with tempfile.TemporaryDirectory(prefix='awft-provider-probe-') as directory:
            classes=Path(directory);classpath=os.pathsep.join(map(str,jars))
            sources=[REPO/'compat/living-world/src/worldfortwo/living/WorldCharacters.java',
                     REPO/'compat/living-world/src/worldfortwo/living/mixin/ProviderConfigMixin.java',
                     REPO/'proposals/living-world/mods/probes/ProviderPolicySelfTest.java']
            compiled=subprocess.run([str(jdk/'javac.exe'),'--release','21','-proc:none','-encoding','UTF-8','-cp',classpath,'-d',str(classes),*map(str,sources)],capture_output=True,text=True,timeout=30)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            run=subprocess.run([str(jdk/'java.exe'),'-Xmx64m','-cp',str(classes)+os.pathsep+classpath,'ProviderPolicySelfTest'],capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn('Actual provider policy callback passed',run.stdout)

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
