"""Small original provenance fixtures; no captured world or inventory data."""
import unittest
import nbtlib
from tools.artistic_eastern_residual_retirement import source_relation,stock_hold


class ResidualOwnership(unittest.TestCase):
    def test_native_join_variation_cannot_hide_reorientation_or_a_different_block(self):
        old='mcwroofs:red_terracotta_roof[facing=north,half=bottom,shape=straight]'
        self.assertEqual(source_relation(old,old.replace('straight','outer_left')),'NATIVE_ROOF_CONNECTION')
        self.assertTrue(source_relation(old,old.replace('north','east').replace('straight','outer_left')).startswith('HOLD'))
        self.assertTrue(source_relation(old,old.replace('red_terracotta','dark_oak')).startswith('HOLD'))

    def test_pinned_sparse_defaults_do_not_authorize_changed_color_or_water(self):
        old='handcrafted:spruce_nightstand[facing=west]'
        self.assertEqual(source_relation(old,'handcrafted:spruce_nightstand[color=none,facing=west,waterlogged=false]'),
            'PINNED_DEFAULT_PROPERTIES_OMITTED_BY_ORIGINAL_SOURCE')
        self.assertTrue(source_relation(old,'handcrafted:spruce_nightstand[color=red,facing=west,waterlogged=false]').startswith('HOLD'))
        self.assertTrue(source_relation(old,'handcrafted:spruce_nightstand[color=none,facing=west,waterlogged=true]').startswith('HOLD'))

    def test_literal_component_encoding_does_not_waive_real_renaming(self):
        authored=nbtlib.Compound({'CustomName':nbtlib.String('{"text":"Original AI shelf"}')})
        actual=nbtlib.Compound({'id':nbtlib.String('supplementaries:item_shelf'),'CustomName':nbtlib.String('"Original AI shelf"')})
        self.assertIsNone(stock_hold(actual,authored))
        actual['CustomName']=nbtlib.String('"Personal renamed shelf"')
        self.assertIsNotNone(stock_hold(actual,authored))

    def test_only_exact_false_default_ink_and_unchanged_sign_text_are_disposable(self):
        authored=nbtlib.parse_nbt('{is_waxed:1b,front_text:{color:"black",has_glowing_text:0b,messages:[\'{"text":"Original AI shop"}\',\'""\',\'""\',\'""\']}}')
        actual=nbtlib.Compound(authored);actual['id']=nbtlib.String('minecraft:sign')
        actual['neoforge:attachments']=nbtlib.Compound({'supplementaries:antique_ink':nbtlib.Byte(0)})
        self.assertIsNone(stock_hold(actual,authored))
        actual['neoforge:attachments']['supplementaries:antique_ink']=nbtlib.Byte(1)
        self.assertIsNotNone(stock_hold(actual,authored))
        actual['neoforge:attachments']['supplementaries:antique_ink']=nbtlib.Byte(0)
        actual['front_text']=nbtlib.Compound(actual['front_text']);actual['front_text']['color']=nbtlib.String('red')
        self.assertIsNotNone(stock_hold(actual,authored))


if __name__=='__main__':unittest.main()
