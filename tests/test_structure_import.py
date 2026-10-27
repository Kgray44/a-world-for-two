"""Small original format fixtures; no downloaded schematic geometry is stored."""
import copy
import gzip
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from control_room.common import UserError
from tools.structure_import import (contextual_legacy, legacy_geometry, litematic_geometry,
    read_source, rotate_position, rotate_record, state_string)


def packed(indices, bits):
    # Deliberately pack bit-by-bit, independently of the decoder's word shifts.
    words=[0]*((len(indices)*bits+63)//64)
    for ordinal,value in enumerate(indices):
        for bit in range(bits):
            if value & (1<<bit):
                offset=ordinal*bits+bit;words[offset//64] |= 1<<(offset%64)
    return [v-(1<<64) if v>=1<<63 else v for v in words]


def lite(size, palette, indices, position=(0,0,0)):
    return {'Version':7,'SubVersion':1,'Regions':{'original-fixture':{
        'Size':dict(zip(('x','y','z'),size)),'Position':dict(zip(('x','y','z'),position)),
        'BlockStatePalette':palette,'BlockStates':packed(indices,max(2,(len(palette)-1).bit_length()))}}}


def alpha(size, ids, metadata, tiles=()):
    return dict(zip(('Width','Height','Length'),size),Materials='Alpha',Blocks=ids,Data=metadata,
                TileEntities=list(tiles),Entities=[])


def table(states):
    return {'minecraft':'1.21.1','data_version':3955,'native_flattened_schema':1451,
            'states':{str(k):v for k,v in states.items()}}


class OriginalFormatTests(unittest.TestCase):
    def test_signed_alpha_bytes_and_non_cubic_yzx_addressing(self):
        doc=alpha((2,2,3),[0]*11+[-112],[0]*11+[1])
        result=legacy_geometry(doc)
        self.assertEqual(len(result),12)
        self.assertEqual(result[1,1,2],2305)
        for mutate in (lambda d:d.update(Width=-2),lambda d:d['Data'].pop(),
                       lambda d:d['Data'].__setitem__(0,16),lambda d:d['Blocks'].__setitem__(0,256),
                       lambda d:d.update(AddBlocks=[0])):
            bad=copy.deepcopy(doc);mutate(bad)
            with self.assertRaises(UserError):legacy_geometry(bad)

    def test_cross_word_palette_bits_signed_words_and_negative_extent(self):
        palette=[{'Name':'minecraft:air'}]+[{'Name':'fixture:block_'+str(n)} for n in range(1,18)]
        indices=[n%18 for n in range(20)]
        result=litematic_geometry(lite((-5,2,-2),palette,indices,(10,4,20)))
        self.assertEqual(result[6,4,19],palette[0])
        # Ordinal 12 starts at bit60, crossing the signed 64-bit boundary.
        self.assertEqual(result[8,5,19],palette[12])
        self.assertEqual(result[10,5,20],palette[1])
        self.assertEqual(len(result),20)

    def test_exact_packed_length_invalid_index_overlap_and_total_bound(self):
        palette=[{'Name':'minecraft:air'},{'Name':'minecraft:stone'},{'Name':'minecraft:dirt'}]
        good=lite((2,1,1),palette,[1,2])
        for mutate in (lambda d:d['Regions']['original-fixture']['BlockStates'].append(0),
                       lambda d:d['Regions']['original-fixture'].update(BlockStates=[3]),
                       lambda d:d.update(Version=7.0)):
            bad=copy.deepcopy(good);mutate(bad)
            with self.assertRaises(UserError):litematic_geometry(bad)
        overlap=copy.deepcopy(good);overlap['Regions']['overlap']=copy.deepcopy(overlap['Regions']['original-fixture'])
        with self.assertRaisesRegex(UserError,'Overlapping'):litematic_geometry(overlap)
        bounded=lite((5,2,4),palette,[0]*40)
        second=copy.deepcopy(bounded['Regions']['original-fixture']);second['Position']['x']=10
        bounded['Regions']['second']=second
        with patch('tools.structure_import.MAX_VOLUME',64),self.assertRaisesRegex(UserError,'Combined'):
            litematic_geometry(bounded)

    def test_gzip_root_truncation_and_decompression_bound(self):
        # Named root compound with an empty name and one original string tag.
        raw=b'\x0a\x00\x00\x08\x00\x01x'+struct.pack('>H',20)+b'a'*20+b'\x00'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.nbt';path.write_bytes(gzip.compress(raw))
            self.assertEqual(read_source(path),{'x':'a'*20})
            with patch('tools.structure_import.MAX_DECODED',16),self.assertRaisesRegex(UserError,'decompression'):
                read_source(path)
            path.write_bytes(b'not gzip')
            with self.assertRaises(UserError):read_source(path)
            path.write_bytes(gzip.compress(raw[:-2]))
            with self.assertRaises(UserError):read_source(path)

    def test_state_atoms_and_actual_registry_properties_refuse_injection(self):
        registry={'blocks':{'fixture:door':{'facing':['north']}}}
        self.assertEqual(state_string({'Name':'fixture:door','Properties':{'facing':'north'}},registry),
                         'fixture:door[facing=north]')
        for row in ({'Name':'minecraft:stone run evil'}, {'Name':'minecraft:stone','Command':'anything'},
                    {'Name':'fixture:door','Properties':{'facing':'north]'}},
                    {'Name':'fixture:door','Properties':{'facing':'south'}}):
            with self.assertRaises(UserError):state_string(row,registry)

    def test_rotation_preserves_handedness_and_rotates_all_cardinal_fields(self):
        row={'Name':'fixture:joined','Properties':{'facing':'north','axis':'x','rotation':'15',
             'north':'true','east':'false','south':'low','west':'none','hinge':'left','shape':'inner_right'}}
        once=rotate_record(row,1)['Properties']
        self.assertEqual((once['facing'],once['axis'],once['rotation']),('east','z','3'))
        self.assertEqual((once['east'],once['south'],once['west'],once['north']),('true','false','low','none'))
        self.assertEqual((once['hinge'],once['shape']),('left','inner_right'))
        value=row
        for _ in range(4):value=rotate_record(value,1)
        self.assertEqual(value,row)
        self.assertEqual(rotate_position((33,27,20),(34,28,21),1),(0,27,33))
        for p in ((34,0,0),(0,0),(0,True,0)):
            with self.assertRaises(UserError):rotate_position(p,(34,28,21),1)


class LegacyContextTests(unittest.TestCase):
    def test_door_halves_use_lower_direction_and_upper_hinge(self):
        doc=alpha((1,2,1),[64,64],[3,9])
        rows=table({1027:{'Name':'minecraft:oak_door','Properties':{
            'half':'lower','facing':'north','open':'false','hinge':'right','powered':'false'}},
            1033:{'Name':'minecraft:oak_door','Properties':{
            'half':'upper','facing':'east','open':'false','hinge':'right','powered':'false'}}})
        geometry,_,_=contextual_legacy(doc,rows)
        self.assertEqual(geometry[0,1,0]['Properties']['facing'],'north')
        self.assertEqual(geometry[0,0,0]['Properties']['hinge'],'right')
        bad=copy.deepcopy(doc);bad['Data'][1]=0
        with self.assertRaises(UserError):contextual_legacy(bad,rows)

    def test_floor_skull_is_not_a_piston_and_requires_own_tile_context(self):
        tile={'id':'Skull','x':0,'y':0,'z':0,'SkullType':1,'Rot':14}
        doc=alpha((1,1,1),[-112],[1],[tile])
        rows=table({2305:{'Name':'%%FILTER_ME%%','Properties':{'nodrop':'false','facing':'up'}}})
        preserved=copy.deepcopy(rows)
        geometry,_,notes=contextual_legacy(doc,rows)
        self.assertEqual(geometry[0,0,0],{'Name':'minecraft:wither_skeleton_skull',
                         'Properties':{'rotation':'14','waterlogged':'false'}})
        self.assertEqual(rows,preserved)
        self.assertEqual(notes['source_entities_excluded'],0)
        doc['TileEntities']=[]
        with self.assertRaisesRegex(UserError,'SkullType'):contextual_legacy(doc,rows)

    def test_beds_pair_direction_and_legacy_connectivity_is_explicitly_pending(self):
        doc=alpha((1,1,2),[26,26],[10,2])
        rows=table({426:{'Name':'minecraft:red_bed','Properties':{'part':'head','facing':'north','occupied':'false'}},
                    418:{'Name':'minecraft:red_bed','Properties':{'part':'foot','facing':'north','occupied':'false'}}})
        self.assertEqual(len(contextual_legacy(doc,rows)[0]),2)
        wrong=copy.deepcopy(rows);wrong['states']['418']['Properties']['facing']='south'
        with self.assertRaisesRegex(UserError,'bed direction'):contextual_legacy(doc,wrong)
        fence=alpha((1,1,1),[85],[0])
        fixed=table({1360:{'Name':'minecraft:oak_fence','Properties':dict.fromkeys(('north','east','south','west'),'false')}})
        geometry,_,notes=contextual_legacy(fence,fixed)
        self.assertEqual(geometry[0,0,0]['Properties'],{})
        self.assertEqual(len(notes['native_connectivity_pending']),1)


if __name__=='__main__':unittest.main()
