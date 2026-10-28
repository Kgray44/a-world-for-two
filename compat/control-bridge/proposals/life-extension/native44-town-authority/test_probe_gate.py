import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('town_probe_gate',Path(__file__).with_name('probe_gate.py'))
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)


class FailClosedProbeGateTests(unittest.TestCase):
    def test_rejected_gate_cannot_launch_any_child(self):
        calls=[]
        with self.assertRaises(gate.GateRefused):gate.after_gate(lambda:gate.MIN_AVAILABLE,lambda:calls.append('launched'))
        self.assertEqual(calls,[])

    def test_unknown_or_failed_gate_never_launches(self):
        calls=[]
        for value in (None,False,'2000000000'):
            with self.assertRaises(gate.GateRefused):gate.after_gate(lambda:value,lambda:calls.append('launched'))
        def failed():raise OSError('read-only gate failed')
        with self.assertRaises(OSError):gate.after_gate(failed,lambda:calls.append('launched'))
        self.assertEqual(calls,[])

    def test_each_serial_probe_rechecks_before_launch(self):
        samples=iter((gate.MIN_AVAILABLE+1,gate.MIN_AVAILABLE-1));calls=[]
        self.assertEqual(gate.after_gate(lambda:next(samples),lambda:calls.append('first'))[0],gate.MIN_AVAILABLE+1)
        with self.assertRaises(gate.GateRefused):gate.after_gate(lambda:next(samples),lambda:calls.append('second'))
        self.assertEqual(calls,['first'])

    def test_reusable_java_wrapper_keeps_gate_and_launch_in_one_branch(self):
        calls=[];command=['C:/Program Files/Java/jdk-21.0.10/bin/java.exe','-Xmx64M','-XX:ActiveProcessorCount=1','FixtureOnly']
        with self.assertRaises(gate.GateRefused):gate.run_java(command,timeout=30,gate=lambda:0,launcher=lambda *a,**k:calls.append(a))
        self.assertEqual(calls,[])
        result=gate.run_java(command,timeout=30,gate=lambda:gate.MIN_AVAILABLE+1,launcher=lambda *a,**k:'fixture child result')
        self.assertEqual(result[1],'fixture child result')


if __name__=='__main__':unittest.main()
