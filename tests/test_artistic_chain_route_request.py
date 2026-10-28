"""Actual binary-region reader boundaries and original route coverage, no runtime proof."""
import hashlib
import struct
import unittest
import zlib
from control_room.common import UserError
from tools.artistic_chain_route_request import NODES,STOCK,endpoint_chunks,chunk_document


def compound(cx,cz,status='minecraft:full'):
    def name(s):
        raw=s.encode();return struct.pack('>H',len(raw))+raw
    return (b'\x0a\x00\x00'+b'\x03'+name('xPos')+struct.pack('>i',cx)
            +b'\x03'+name('zPos')+struct.pack('>i',cz)+b'\x08'+name('Status')+name(status)+b'\x00')


def region(cx,cz,payload):
    raw=bytearray(12288);slot=((cz&31)*32+(cx&31))*4;raw[slot:slot+4]=struct.pack('>I',(2<<8)|1)
    body=b'\x02'+zlib.compress(payload);raw[8192:8196]=struct.pack('>I',len(body));raw[8196:8196+len(body)]=body
    return raw


class ChainRouteSourceBoundaryTests(unittest.TestCase):
    def test_five_by_five_source_is_strictly_larger_than_geometry_three_by_three(self):
        centers,required=endpoint_chunks()
        three={(x+dx,z+dz)for x,z in centers for dx in(-1,0,1)for dz in(-1,0,1)}
        self.assertLess(three,required);self.assertEqual(len(required),217)
        for x,z in centers:
            self.assertIn((x-2,z-2),required);self.assertIn((x+2,z+2),required)
        self.assertEqual(NODES[-1],(1100,72,-1256));self.assertEqual(STOCK,(1101,65,-1257))

    def test_real_region_header_and_nbt_status_hash_survive_negative_coordinates(self):
        cx,cz=68,-79;payload=compound(cx,cz);raw=region(cx,cz,payload)
        doc,sha=chunk_document(raw,cx,cz)
        self.assertEqual((doc['xPos'],doc['zPos'],doc['Status']),(cx,cz,'minecraft:full'))
        self.assertEqual(sha,hashlib.sha256(payload).hexdigest())

    def test_missing_saved_chunk_is_unknown_not_an_air_or_full_default(self):
        with self.assertRaisesRegex(UserError,'No SAVED chunk'):chunk_document(bytearray(8192),3,-8)

    def test_external_mode_corrupt_sector_and_truncated_zlib_refuse(self):
        cx,cz=2,-2;raw=region(cx,cz,compound(cx,cz));bad=bytearray(raw);bad[8196]=130
        with self.assertRaises(UserError):chunk_document(bad,cx,cz)
        bad=bytearray(raw);slot=((cz&31)*32+(cx&31))*4;bad[slot:slot+4]=struct.pack('>I',(4<<8)|1)
        with self.assertRaises(UserError):chunk_document(bad,cx,cz)
        bad=bytearray(raw);bad[8192:8196]=struct.pack('>I',3)
        with self.assertRaises(UserError):chunk_document(bad,cx,cz)


if __name__=='__main__':unittest.main()
