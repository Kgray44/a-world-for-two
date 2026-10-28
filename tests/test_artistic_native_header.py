"""Real Java admission-header limits, without invoking or simulating Minecraft."""
import unittest

from control_room.common import UserError
from tools.artistic_review import construction_bounds,construction_header


class NativeConstructionHeaderTests(unittest.TestCase):
    def test_missing_or_malformed_bounds_cannot_reach_console(self):
        for value in (None,[],[0,0,1],[0,0,1,True],[2,0,1,1]):
            with self.subTest(value=value),self.assertRaises(UserError):
                construction_bounds({} if value is None else {'bounds':value})

    def test_exact_java_512_limit_requires_splitting_a_whole_shore(self):
        self.assertEqual(construction_bounds({'bounds':[912,-1200,1352,-688]}),[912,-1200,1352,-688])
        with self.assertRaises(UserError):
            construction_bounds({'bounds':[912,-1200,1352,-616]})

    def test_real_native_tag_parser_receives_snbt_text_not_a_json_object(self):
        plan={'bounds':[0,0,1,1],'commands':[],
              'block_entities':[{'pos':[0,64,0],'nbt':{'id':'minecraft:barrel','Items':[]}}]}
        with self.assertRaisesRegex(UserError,'SNBT'):
            construction_header(plan)
        plan['block_entities'][0]['nbt']='{id:"minecraft:barrel",Items:[]}'
        construction_header(plan)


if __name__=='__main__':unittest.main()
