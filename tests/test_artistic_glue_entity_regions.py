"""Binary record boundaries only; no world, live files or native entity action."""
import struct
import unittest
import zlib
from control_room.common import UserError
from tools.artistic_bridge_admission import entity_chunk_record


def name(value):
    raw = value.encode();return struct.pack('>H', len(raw))+raw


def nbt(cx=62, cz=-67, version=3955, version_type=3):
    number = struct.pack('>i' if version_type == 3 else '>q', version)
    return (b'\x0a\x00\x00'+bytes([version_type])+name('DataVersion')+number
        +b'\x0b'+name('Position')+struct.pack('>iii', 2, cx, cz)
        +b'\x09'+name('Entities')+b'\x0a'+struct.pack('>i', 0)+b'\x00')


def record(payload=None, padded=False, extra_compressed=b'', mode=2):
    packed = zlib.compress(nbt() if payload is None else payload)+extra_compressed
    body = bytes([mode])+packed
    raw = bytearray(8192)+struct.pack('>I', len(body))+body
    if padded:raw.extend(b'\x00'*(12288-len(raw)))
    return raw


class GlueEntityRecordBoundaryTests(unittest.TestCase):
    def test_intact_unpadded_tail_matches_padded_plain_and_complete_typed_NBT(self):
        plain, typed = entity_chunk_record(record(), 2, 1, (62, -67))
        self.assertEqual((plain, typed), entity_chunk_record(record(padded=True), 2, 1, (62, -67)))
        self.assertEqual(typed[1]['Position'], [11, [62, -67]])
        self.assertEqual(typed[1]['DataVersion'], [3, 3955])

    def test_missing_payload_byte_or_missing_record_header_never_becomes_padding(self):
        for raw in (record()[:-1], bytearray(8195)):
            with self.subTest(bytes=len(raw)), self.assertRaises(UserError):
                entity_chunk_record(raw, 2, 1, (62, -67))

    def test_invalid_allocated_sectors_and_counts_refuse(self):
        for sector, count in ((1, 1), (2, 0), (2, 2), (3, 1), (0, 1)):
            with self.subTest(sector=sector, count=count), self.assertRaises(UserError):
                entity_chunk_record(record(), sector, count, (62, -67))

    def test_bad_compression_external_mode_and_unfinished_stream_refuse(self):
        for raw in (record(mode=130), record(extra_compressed=zlib.compress(b'foreign'))):
            with self.assertRaises(UserError):entity_chunk_record(raw, 2, 1, (62, -67))
        raw = record();raw[8192:8196] = struct.pack('>I', len(raw)-8196-1)
        with self.assertRaises(UserError):entity_chunk_record(raw, 2, 1, (62, -67))

    def test_coordinates_version_and_native_numeric_tag_types_are_exact(self):
        for payload in (nbt(cx=63), nbt(cz=-66), nbt(version=4903), nbt(version_type=4)):
            with self.assertRaises(UserError):entity_chunk_record(record(payload), 2, 1, (62, -67))
