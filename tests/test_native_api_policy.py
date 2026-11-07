"""Real JVM execution of pure native policy/accounting source; no API or Minecraft."""
import os
import shutil
import subprocess
import tempfile
import unittest
import queue
import threading
from pathlib import Path
from control_room.common import REPO
from tools.living_world_upstream import reserve_allocation


class NativeApiPolicyTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows msvcrt/Java lock interoperability')
    def test_windows_spending_lock_is_shared_between_python_and_java(self):
        import msvcrt
        jdk=Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
        if not (jdk/'javac.exe').is_file():
            self.skipTest('Existing Java 21 compiler required')
        reserve_allocation(Path(tempfile.gettempdir())/'awft-spending-lock')
        with tempfile.TemporaryDirectory(prefix='awft-spending-lock-') as directory:
            sources=[REPO/'compat/living-world/src/worldfortwo/living/SharedSpendingLock.java',REPO/'proposals/living-world/mods/probes/SpendingLockSelfTest.java']
            compiled=subprocess.run([str(jdk/'javac.exe'),'--release','21','-d',directory,*map(str,sources)],capture_output=True,text=True,timeout=30)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            lockfile=Path(directory)/'spending.lock';lockfile.write_bytes(b'\0')
            command=[str(jdk/'java.exe'),'-Xmx32m','-cp',directory,'SpendingLockSelfTest',str(lockfile)]
            with lockfile.open('r+b') as stream:
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                try:
                    blocked=subprocess.run(command+['try'],capture_output=True,text=True,timeout=5)
                    self.assertEqual(blocked.returncode,0,blocked.stderr);self.assertEqual(blocked.stdout.strip(),'busy')
                finally:
                    stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
                owned=subprocess.Popen(command+['hold'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                try:
                    output=queue.Queue()
                    threading.Thread(target=lambda:output.put(owned.stdout.readline()),daemon=True).start()
                    self.assertEqual(output.get(timeout=5).strip(),'held')
                    stream.seek(0)
                    with self.assertRaises(OSError):msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                finally:
                    try:owned.communicate('\n',timeout=5)
                    except subprocess.TimeoutExpired:owned.kill();owned.communicate(timeout=5)
                self.assertEqual(owned.returncode,0)
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)

    def test_native_model_generation_and_usage_policy(self):
        jdk=Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
        javac=str(jdk/'javac.exe') if (jdk/'javac.exe').is_file() else shutil.which('javac')
        java=str(jdk/'java.exe') if (jdk/'java.exe').is_file() else shutil.which('java')
        gson=Path(os.environ.get('AWFT_GSON_JAR',r'D:\A World for Two\server\libraries\com\google\code\gson\gson\2.10.1\gson-2.10.1.jar'))
        if not javac or not java or not gson.is_file():
            self.skipTest('Existing Java 21/Gson inputs required; no downloads or API calls')
        reserve_allocation(Path(tempfile.gettempdir())/'awft-native-api-policy')
        with tempfile.TemporaryDirectory(prefix='awft-native-api-policy-') as directory:
            sources=[REPO/'compat/living-world/src/worldfortwo/living'/name for name in ('WorldCharacters.java','NativeRequestPolicy.java','NativeUsage.java')]
            sources.append(REPO/'proposals/living-world/mods/probes/NativeApiPolicySelfTest.java')
            compiled=subprocess.run([javac,'--release','21','-encoding','UTF-8','-cp',str(gson),'-d',directory,*map(str,sources)],capture_output=True,text=True,timeout=30)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            run=subprocess.run([java,'-Xmx64m','-cp',directory+os.pathsep+str(gson),'NativeApiPolicySelfTest'],capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn('Native model policy, generation parameters, private usage',run.stdout)


if __name__=='__main__':
    unittest.main()
