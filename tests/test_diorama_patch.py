import tempfile
import unittest
from pathlib import Path

from control_room.common import UserError
from tools.diorama_patch import build


class DioramaPatchBounds(unittest.TestCase):
    def test_unreviewed_bytes_refuse_before_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'different.jar'
            source.write_bytes(b'x' * 924656)
            output = root/'build'
            with self.assertRaisesRegex(UserError, 'exact reviewed official'):
                build(source, output, root/'libraries')
            self.assertFalse(output.exists())
