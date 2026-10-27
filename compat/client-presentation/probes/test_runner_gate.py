"""Only the no-launch CLI gate; actual Java semantics remain explicitly deferred."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch


RUNNER = Path(__file__).with_name('run_smallships_config_probe.py')


class RunnerGate(unittest.TestCase):
    def forbidden_side_effects(self, stack):
        operations = ('subprocess.Popen', 'subprocess.run', 'pathlib.Path.mkdir',
                      'pathlib.Path.write_text', 'pathlib.Path.write_bytes')
        return [stack.enter_context(patch(name, side_effect=AssertionError('No-launch gate crossed: '+name)))
                for name in operations]

    def test_default_reports_pending_without_any_process_or_write(self):
        output = io.StringIO()
        with ExitStack() as stack:
            forbidden = self.forbidden_side_effects(stack)
            stack.enter_context(patch('sys.argv', [str(RUNNER)]))
            stack.enter_context(redirect_stdout(output))
            runpy.run_path(str(RUNNER), run_name='__main__')
            for operation in forbidden:
                operation.assert_not_called()
        actual = json.loads(output.getvalue())
        self.assertEqual(actual['status'], 'pending: not executed')
        self.assertFalse(actual['java_launched'])
        self.assertFalse(actual['writes'])

    def test_execution_flag_without_artifact_still_cannot_launch_or_write(self):
        with ExitStack() as stack:
            forbidden = self.forbidden_side_effects(stack)
            stack.enter_context(patch('sys.argv', [str(RUNNER), '--execute-after-resource-window']))
            stack.enter_context(redirect_stderr(io.StringIO()))
            with self.assertRaises(SystemExit) as exited:
                runpy.run_path(str(RUNNER), run_name='__main__')
            self.assertEqual(exited.exception.code, 2)
            for operation in forbidden:
                operation.assert_not_called()


if __name__ == '__main__':
    unittest.main()
