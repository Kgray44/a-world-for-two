import json
import unittest

from control_room.common import UserError
from tools.graphics_preset import fresh_options, material_text, select_text


class TexturePresets(unittest.TestCase):
    def test_material_selection_preserves_unrelated_options(self):
        before = '# owner settings\nshadowDistance=128.0\nPARALLAX_DEPTH=0.25\n'
        after = material_text(before, {'PARALLAX_DEPTH': '0.10', 'ADVANCED_MATERIALS': 'true'})
        self.assertIn('# owner settings\nshadowDistance=128.0\n', after)
        self.assertIn('PARALLAX_DEPTH=0.10\n', after)
        self.assertIn('ADVANCED_MATERIALS=true\n', after)
        with self.assertRaises(UserError):
            material_text('PARALLAX_DEPTH=0.2\nPARALLAX_DEPTH=0.3\n', {'PARALLAX_DEPTH': '0.10'})

    def test_fresh_import_preserves_animation_and_has_one_base(self):
        options = fresh_options({'mods': [
            {'slug': slug, 'filename': slug+'.zip', 'kind': 'resourcepack'}
            for slug in ('fresh-animations', 'stylista', 'roundista', 'nautilus3d')]
            + [{'kind': 'mod', 'request': 'diorama'}]})
        packs = json.loads(next(line.split(':', 1)[1] for line in options.splitlines() if line.startswith('resourcePacks:')))
        self.assertEqual(packs, ['vanilla', 'file/fresh-animations.zip', 'file/stylista.zip', 'file/nautilus3d.zip'])
        self.assertIn('key_key.diorama.open_map:key.keyboard.f8', options)

    def test_switch_preserves_settings_and_other_packs(self):
        text = 'music:0.4\nresourcePacks:["vanilla","file/user.zip","file/stylista.zip","file/nautilus.zip"]\nrenderDistance:10\n'
        actual = select_text(text, 'file/roundista.zip', 'file/nautilus.zip',
                             {'file/stylista.zip', 'file/roundista.zip', 'file/nautilus.zip'})
        self.assertIn('music:0.4\n', actual)
        self.assertIn('renderDistance:10\n', actual)
        packs = json.loads(actual.splitlines()[1].split(':', 1)[1])
        self.assertEqual(packs, ['vanilla', 'file/user.zip', 'file/roundista.zip', 'file/nautilus.zip'])
        self.assertEqual(actual, select_text(actual, 'file/roundista.zip', 'file/nautilus.zip', set(packs[2:])))

    def test_missing_line_and_bad_duplicate(self):
        self.assertIn('\nresourcePacks:', select_text('music:0.4', 'base', 'overlay', set()))
        with self.assertRaises(UserError):
            select_text('resourcePacks:[]\nresourcePacks:[]\n', 'a', 'b', set())


if __name__ == '__main__':
    unittest.main()
