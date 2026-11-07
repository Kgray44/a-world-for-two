import unittest
from control_room.common import UserError
from tools.build_bridge import validate_runtime_identity


class RuntimeIdentityTests(unittest.TestCase):
    def test_all_native_authorities_have_the_exact_build_identity(self):
        current = '\n'.join('new Helper("0.1.0-candidate.55","0.6.41", gate);' for _ in range(13))
        validate_runtime_identity(current, '0.1.0-candidate.55', '0.6.41')
        for invalid in (current.replace('candidate.55', 'candidate.53', 1),
                        current.replace('0.6.41', '0.6.39', 1), current + current,
                        current.split('\n', 1)[1], ''):
            with self.subTest(invalid=invalid[:70]), self.assertRaises(UserError):
                validate_runtime_identity(invalid, '0.1.0-candidate.55', '0.6.41')


if __name__ == '__main__':
    unittest.main()
