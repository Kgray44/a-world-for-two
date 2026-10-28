import hashlib
import struct
import unittest
import uuid
import zlib
from types import SimpleNamespace

from control_room.common import UserError
from tools.artistic_south_forest import LIFE,residents
from tools.habitat_life import census,decode_entity_chunks,entity_uuid,final_plaza_clear,make_recipes,members_for_group


def text(value):
    raw=value.encode();return struct.pack('>H',len(raw))+raw


def compound(row):
    result=b''
    for key,value in row.items():
        if isinstance(value,str):result+=b'\x08'+text(key)+text(value)
        elif key=='UUID':result+=b'\x0b'+text(key)+struct.pack('>i4i',4,*value)
        elif key=='Position':result+=b'\x0b'+text(key)+struct.pack('>i2i',2,*value)
        elif key=='DataVersion':result+=b'\x03'+text(key)+struct.pack('>i',value)
        elif key=='Pos':result+=b'\x09'+text(key)+b'\x06'+struct.pack('>i3d',3,*value)
        elif key=='Tags':result+=b'\x09'+text(key)+b'\x08'+struct.pack('>i',len(value))+b''.join(text(v) for v in value)
        elif key in ('Passengers','Entities'):result+=b'\x09'+text(key)+b'\x0a'+struct.pack('>i',len(value))+b''.join(compound(v) for v in value)
        else:raise ValueError(key)
    return result+b'\x00'


def region(rows,position=(0,0),version=3955,padded=True,extra=b'',decoded_extra=b'',mode=2):
    raw=b'\x0a\x00\x00'+compound({'DataVersion':version,'Position':position,'Entities':rows})+decoded_extra
    packed=(raw if mode==3 else zlib.compress(raw,wbits=31 if mode==1 else 15))+extra
    payload=struct.pack('>i',len(packed)+1)+bytes([mode])+packed
    sectors=(len(payload)+4095)//4096
    header=struct.pack('>I',2*256+sectors)+bytes(8192-4)
    return header+payload+(bytes(sectors*4096-len(payload)) if padded else b'')


class Snapshot:
    prefix='world/Owned/region/'
    def __init__(self,raw):
        name='world/Owned/entities/r.0.0.mca';self.files={name:{'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}
        self.archive=SimpleNamespace(getinfo=lambda key:SimpleNamespace(file_size=len(raw)),read=lambda key:raw)


class Ground:
    def column(self,x,z):return {'kind':'dry','surface_y':65,'state':'minecraft:grass_block[snowy=false]'}
    def state(self,x,y,z):return 'minecraft:grass_block[snowy=false]' if y==65 else 'minecraft:air'


class HabitatLifeTests(unittest.TestCase):
    def test_complete_unpadded_final_record_is_identical_to_padded_entity_census(self):
        padded=region([]);unpadded=region([],padded=False)
        self.assertLess(len(unpadded),len(padded))
        self.assertEqual(list(decode_entity_chunks(unpadded,(0,0))),list(decode_entity_chunks(padded,(0,0))))
        for mode in (1,2,3):
            self.assertEqual(list(decode_entity_chunks(region([],padded=False,mode=mode))),
                             list(decode_entity_chunks(padded)))

    def test_missing_record_bytes_and_fabricated_sector_extent_remain_refused(self):
        raw=region([],padded=False)
        for changed in (raw[:-1],raw[:8196],struct.pack('>I',2*256+2)+raw[4:]):
            with self.subTest(size=len(changed)),self.assertRaises(UserError):
                list(decode_entity_chunks(changed))
        truncated=bytearray(raw[:-1]);truncated[8192:8196]=struct.pack('>I',int.from_bytes(raw[8192:8196],'big')-1)
        with self.assertRaises(UserError):list(decode_entity_chunks(truncated))

    def test_trailing_compressed_data_or_nbt_and_wrong_record_identity_are_refused(self):
        for raw,expected_region in ((region([],extra=b'untrusted-tail'),None),
                                    (region([],decoded_extra=b'\x00'),None),
                                    (region([],position=(1,0)),None),
                                    (region([]),(1,0)),(region([],version=999999),None)):
            with self.subTest(expected_region=expected_region),self.assertRaises(UserError):
                list(decode_entity_chunks(raw,expected_region))
        raw=bytearray(region([],padded=False));raw[8196]=130
        with self.assertRaises(UserError):list(decode_entity_chunks(raw))

    def test_saved_UUID_formats_and_malformed_identity(self):
        key=uuid.UUID(int=1);words=list(struct.unpack('>4i',key.bytes))
        self.assertEqual(entity_uuid({'UUID':words}),str(key))
        self.assertEqual(entity_uuid({'UUIDMost':0,'UUIDLeast':1}),str(key))
        with self.assertRaises(UserError):entity_uuid({'UUID':[1,2,3]})

    def test_complete_census_finds_passenger_without_exporting_unrelated_NBT(self):
        key=uuid.UUID(int=1);tag='awft_life_'+'a'*24
        entity={'id':'naturalist:bird','UUID':list(struct.unpack('>4i',key.bytes)),
                'Pos':[1100.5,66.,-1050.5],'Tags':['awft_life',tag]}
        unrelated={'id':'minecraft:boat','UUID':list(struct.unpack('>4i',uuid.UUID(int=2).bytes)),
                   'Pos':[1100.,65.,-1050.],'Passengers':[entity]}
        result=census(Snapshot(region([unrelated])),[{'uuid':str(key),'member_tag':tag}],'b'*64,'c'*64)
        self.assertEqual(result['saved_entity_records_inspected'],2)
        self.assertEqual(result['matching_requested_UUIDs'],1)
        self.assertTrue(result['members'][0]['expected_tags_present'])
        self.assertNotIn('Passengers',str(result));self.assertFalse(result['unrelated_UUIDs_or_raw_entity_NBT_exported'])
        with self.assertRaises(UserError):census(Snapshot(region([entity,entity])),[{'uuid':str(key),'member_tag':tag}],'b'*64,'c'*64)

    def test_census_corruption_and_saved_player_collision_fail_closed(self):
        key=str(uuid.UUID(int=1));member={'uuid':key,'member_tag':'tag'};snapshot=Snapshot(region([]))
        next(iter(snapshot.files.values()))['sha256']='0'*64
        with self.assertRaises(UserError):census(snapshot,[member],'b'*64,'c'*64)
        snapshot=Snapshot(region([]));snapshot.files['world/Owned/playerdata/'+key+'.dat']={'size':1,'sha256':'0'*64}
        with self.assertRaises(UserError):census(snapshot,[member],'b'*64,'c'*64)

    def test_authenticated_empty_entity_region_is_empty_but_partial_header_is_unknown(self):
        member={'uuid':str(uuid.UUID(int=1)),'member_tag':'tag'}
        result=census(Snapshot(b''),[member],'b'*64,'c'*64)
        self.assertTrue(result['all_requested_UUID_absent'])
        self.assertTrue(result['sources'][0]['empty_no_serialized_payload'])
        with self.assertRaises(UserError):census(Snapshot(b'\x00'),[member],'b'*64,'c'*64)

    def test_group_members_have_distinct_real_footings_and_no_entity_NBT(self):
        reg={'entity_categories':{key:value[0] for key,value in LIFE.items()}}
        group=residents(reg,str(uuid.UUID(int=3)),[(1100,-1050)])[0]
        members=members_for_group(group,Ground())
        self.assertEqual(len(members),len({tuple(v['feet']) for v in members}))
        self.assertTrue(all(len(v['preimage'])==45 for v in members))
        self.assertTrue(all('nbt' not in v and 'NoAI' not in v and 'OwnerUUID' not in v for v in members))
        group['entity']='naturalist:bear'
        with self.assertRaises(UserError):members_for_group(group,Ground())

    def test_small_batches_preserve_cross_batch_unique_population(self):
        reg={'entity_categories':{key:value[0] for key,value in LIFE.items()},'seed':'fixture-only','world_path':'fixture-only'}
        groups=residents(reg,str(uuid.UUID(int=3)),[(1100,-1050),(1140,-1050),(1180,-1050),(1260,-920),(1340,-920)])
        recipe=make_recipes({'population_namespace':str(uuid.UUID(int=3)),'resident_groups':groups},reg,Ground())
        self.assertEqual(len(recipe),3);members=[row for batch in recipe for row in batch['members']]
        self.assertEqual(len(members),len({v['uuid'] for v in members}));self.assertTrue(all(len(r['members'])<=10 for r in recipe))

    def test_final_plaza_includes_AIR_plumbing_and_entire_five_metre_skirt(self):
        registry={'seed':'fixture-only','world_path':'fixture-only'}
        mask={**registry,'blocks':[[1100,65,-1100,0]],'palette':['minecraft:air']}
        with self.assertRaises(UserError):final_plaza_clear({'proposed_geometry':[[1105,80,-1100,'leaf']]},mask,registry)
        final_plaza_clear({'proposed_geometry':[[1106,80,-1100,'leaf']]},mask,registry)
        with self.assertRaises(UserError):final_plaza_clear({'proposed_geometry':[]},{**mask,'seed':'other'},registry)


if __name__=='__main__':unittest.main()
