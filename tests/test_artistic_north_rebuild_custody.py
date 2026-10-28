"""Custody facts must retain types and uncertainty; no native mutation tests."""
import unittest
import nbtlib

from tools.artistic_north_rebuild_custody import typed, typed_subset, inventory_facts, classify


class NorthRebuildCustodyTests(unittest.TestCase):
    def test_numeric_widths_and_full_item_components_survive(self):
        be=nbtlib.parse_nbt('{Items:[{Slot:0b,id:"minecraft:diamond",count:1,components:{"minecraft:custom_data":{serial:9223372036854775807L,flag:1b}}}]}')
        out=typed(be)['value']['Items']['value'][0]['value']
        self.assertEqual(out['Slot'],{'tag':'Byte','value':0})
        self.assertEqual(out['count'],{'tag':'Int','value':1})
        data=out['components']['value']['minecraft:custom_data']['value']
        self.assertEqual(data['serial'],{'tag':'Long','value':9223372036854775807})
        self.assertEqual(data['flag']['tag'],'Byte')

    def test_empty_list_subtype_and_array_kind_are_not_lost(self):
        empty=nbtlib.List[nbtlib.Compound]([])
        self.assertEqual(typed(empty),{'tag':'List','subtype':'Compound','value':[]})
        self.assertFalse(typed_subset(empty,nbtlib.List[nbtlib.String]([])))
        self.assertEqual(typed(nbtlib.LongArray([-(2**63),2**63-1])),{'tag':'LongArray','value':[-(2**63),2**63-1]})
        self.assertFalse(typed_subset(nbtlib.Byte(1),nbtlib.Int(1)))

    def test_absent_items_never_certifies_an_empty_native_container(self):
        facts=inventory_facts(nbtlib.parse_nbt('{id:"example:unrecognized_storage",capacity:27}'))
        self.assertEqual(facts['saved_item_records'],[])
        self.assertIn('PENDING',facts['native_container_instance_class_slots_and_all_components'])
        self.assertFalse(facts['may_delete_or_recreate'])

    def test_loot_and_custom_storage_remain_custody_gates(self):
        be=nbtlib.parse_nbt('{LootTable:"example:unopened",CustomStorage:{items:[{id:"minecraft:book",count:2}]}}')
        facts=inventory_facts(be)
        self.assertEqual(len(facts['unresolved_loot_fields']),1)
        self.assertEqual(facts['saved_item_records'][0]['count'],2)
        self.assertTrue(any(row['path']==['CustomStorage'] for row in facts['saved_inventory_like_fields']))
        self.assertFalse(facts['may_delete_or_recreate'])

    def test_source_similarity_cannot_discard_a_be_or_restore_player_changes(self):
        self.assertEqual(classify('minecraft:air','minecraft:air','minecraft:barrel[facing=up]',is_be=True),
                         'CURRENT_BLOCK_ENTITY_PRESERVE_FULL_TYPED_CUSTODY')
        self.assertEqual(classify('minecraft:stone','minecraft:air','minecraft:air'),
                         'MATERIAL_OR_AIR_DELTA_POSSIBLE_HUMAN_OR_OTHER_WORK_PRESERVE')
        self.assertEqual(classify('minecraft:stone','minecraft:air','minecraft:stone',protected=True),
                         'ACCEPTED_ORIGINAL_PROTECTION_PRESERVE')
        self.assertEqual(classify('minecraft:oak_fence[north=false]','minecraft:air','minecraft:oak_fence[north=true]'),
                         'SAME_ID_STATE_DELTA_NATIVE_SHAPE_OR_HUMAN_ORIGIN_UNPROVEN_PRESERVE')


if __name__=='__main__':unittest.main()
