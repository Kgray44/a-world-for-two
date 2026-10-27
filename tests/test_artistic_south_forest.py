import unittest
import hashlib
import json
from pathlib import Path
import tempfile
import uuid
from collections import OrderedDict
from types import SimpleNamespace

from control_room.common import UserError
from tools.artistic_south_forest import (AIR, LIFE, NATIVE_ANIMAL_JAR, Terrain, TREE_MATERIALS, base, bind_species_evidence, glade_witness,
    native_state, residents, south_component, tree_admission, tree_shape)


def registry():
    blocks={}
    for log,leaves in TREE_MATERIALS.values():
        blocks[log]={'axis':['x','y','z']}
        blocks[leaves]={'distance':[str(n) for n in range(1,8)],
                        'persistent':['true','false'],'waterlogged':['true','false']}
    blocks['regions_unexplored:silver_birch_log']['is_base']=['true','false']
    blocks['regions_unexplored:pine_log'].update(is_stripped=['true','false'],transition_block=['true','false'])
    return {'blocks':blocks,'entity_categories':{key:value[0] for key,value in LIFE.items()}}


class Ground:
    def __init__(self, special=None):self.special=special or {}
    def column(self,x,z):
        return {'x':x,'z':z,'kind':self.special.get((x,z),'dry'),
                'surface_y':65,'state':'minecraft:grass_block[snowy=false]'}
    def state(self,x,y,z):return 'minecraft:air'


class SouthForestTests(unittest.TestCase):
    def test_unknown_chunk_stays_unknown_on_cached_repeat(self):
        terrain=Terrain.__new__(Terrain)
        terrain.key=None;terrain.blocks={};terrain.unknown={};terrain.cache=OrderedDict()
        terrain.snapshot=SimpleNamespace(regions={(2,-3):bytes(8192)})
        self.assertIsNone(terrain.chunk(64,-70))
        self.assertIsNone(terrain.chunk(64,-70))
        self.assertIsNone(terrain.state(1024,80,-1120))
        self.assertEqual(terrain.unknown[(64,-70)],'not saved/generated')

    def test_land_connection_does_not_bridge_water_or_unknown(self):
        rows=[{'x':x,'z':0,'kind':kind} for x,kind in ((0,'dry'),(4,'water'),(8,'dry'),(12,'unknown'))]
        self.assertEqual(south_component(rows,anchor=(0,0)),{(0,0)})
        with self.assertRaises(UserError):south_component(rows,anchor=(4,0))

    def test_whole_crown_and_full_five_metre_skirt_are_checked(self):
        field={(0,1,0):'regions_unexplored:maple_log[axis=y]',
               (3,5,0):'regions_unexplored:red_maple_leaves[distance=7,persistent=true,waterlogged=false]'}
        root=(1100,65,-1060)
        admitted,why=tree_admission(Ground(),root,field,set(),{})
        self.assertIsNone(why);self.assertEqual(len(admitted[0]),2)
        # Air at leaf height does not authorize overhanging a wet/unknown shore.
        for kind in ('water','unknown'):
            result,why=tree_admission(Ground({(1103,-1060):kind}),root,field,set(),{})
            self.assertIsNone(result);self.assertIn('shore',why)
        result,why=tree_admission(Ground(),root,field,{(1103,-1060)}, {})
        self.assertIsNone(result);self.assertIn('skirt',why)
        result,why=tree_admission(Ground({(1108,-1060):'retained_object'}),root,field,set(),{})
        self.assertIsNone(result);self.assertIn('five-metre',why)
        # A known dry crown cannot establish what is five metres beyond it.
        result,why=tree_admission(Ground({(1108,-1060):'unknown'}),root,field,set(),{})
        self.assertIsNone(result);self.assertIn('unknown cell',why)
        # Six metres beyond the outer leaf is outside this finite perimeter.
        result,why=tree_admission(Ground({(1109,-1060):'unknown'}),root,field,set(),{})
        self.assertIsNone(why);self.assertIsNotNone(result)

    def test_native_tree_profiles_have_connected_log_support_and_actual_properties(self):
        reg=registry()
        for kind in TREE_MATERIALS:
            with self.subTest(kind=kind):
                field=tree_shape(reg,kind,10,4,19)
                logs={pos for pos,state in field.items() if base(state).endswith('_log')}
                visited={(0,1,0)};pending=list(visited)
                while pending:
                    x,y,z=pending.pop()
                    for other in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
                        if other in logs and other not in visited:visited.add(other);pending.append(other)
                self.assertEqual(logs,visited)
                self.assertTrue(any(base(state).endswith('_leaves') for state in field.values()))
                self.assertTrue(all('persistent=true' in state and 'waterlogged=false' in state
                                    for state in field.values() if base(state).endswith('_leaves')))
        with self.assertRaises(UserError):native_state(reg,'regions_unexplored:pine_log',axis='y',invented=True)

    def test_resident_identity_survives_order_changes_and_does_not_forge_ownership(self):
        reg=registry();key=str(uuid.UUID(int=1));glades=[(1100,-1060),(1200,-900),(1340,-920)]
        first={r['id']:r for r in residents(reg,key,glades)}
        second={r['id']:r for r in residents(reg,key,list(reversed(glades)))}
        self.assertEqual(first,second)
        ids=[m['uuid'] for row in first.values() for m in row['members']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(all(not r['NoAI'] and not r['OwnerUUID_assigned'] and not r['spawn_executed'] for r in first.values()))
        reg['entity_categories']['naturalist:deer']='monster'
        deer_glade=next((x,z) for x in range(1090,1110) for z in range(-1070,-1050)
                        if residents(registry(),key,[(x,z)])[0]['entity']=='naturalist:deer')
        with self.assertRaises(UserError):residents(reg,key,[deer_glade])

    def test_glade_needs_actual_dry_support_and_three_cell_body_space(self):
        center=(1100,-1060);good=glade_witness(Ground(),center,set())
        self.assertEqual(good['saved_dry_support_columns'],25)
        self.assertEqual(good['body_cells_checked'],75)
        self.assertFalse(good['native_spawn_or_behavior_tested'])
        self.assertIsNone(glade_witness(Ground({(1102,-1058):'water'}),center,set()))
        self.assertIsNone(glade_witness(Ground({(1102,-1058):'unknown'}),center,set()))
        blocked=Ground();blocked.state=lambda x,y,z:'minecraft:stone' if (x,y,z)==(1101,68,-1059) else 'minecraft:air'
        self.assertIsNone(glade_witness(blocked,center,set()))

    def test_pinned_species_receipt_accepts_serialized_path_and_rejects_wrong_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'proof.json'
            row={'entity_id':'naturalist:deer','class':'native.Deer','actual_registry_category':'creature',
                 'inspection_sha256':'a'*64,'registerGoals_new_classes':['PanicGoal']}
            doc={'jar_sha256':NATIVE_ANIMAL_JAR[1],'registry_sha256':'b'*64,'classes':[row]}
            path.write_text(json.dumps(doc),encoding='utf-8')
            proof={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            result={'species_witnesses':{'naturalist:deer':{'native_class':'native.Deer','native_MobCategory':'creature'}}}
            bind_species_evidence(result,proof)
            self.assertEqual(result['species_witnesses']['naturalist:deer']['pinned_native_jar_sha256'],NATIVE_ANIMAL_JAR[1])
            self.assertIn('not claimed',result['native_behavior_witness']['scope'])
            for key,value in (('native_class','other.Deer'),('native_MobCategory','monster')):
                wrong={'native_class':'native.Deer','native_MobCategory':'creature',key:value}
                with self.assertRaises(UserError):bind_species_evidence({'species_witnesses':{'naturalist:deer':wrong}},proof)
            path.write_text('{}',encoding='utf-8')
            with self.assertRaises(UserError):bind_species_evidence(result,proof)


if __name__=='__main__':unittest.main()
