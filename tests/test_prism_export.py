"""Public/local join regressions; native client import is a separate receipt."""
import io
import re
import struct
import unittest

from control_room.common import REPO
from tools.prism_export import LOCAL_SERVER, PUBLIC_SERVER, server_list


def decode_nbt(raw):
    """Independent bounded reader for the standard NBT types used by ServerList."""
    stream=io.BytesIO(raw)
    def read(length):
        value=stream.read(length)
        if len(value)!=length:raise ValueError('Truncated NBT')
        return value
    def text():return read(struct.unpack('>H',read(2))[0]).decode('utf-8')
    def payload(kind):
        if kind==1:return struct.unpack('>b',read(1))[0]
        if kind==8:return text()
        if kind==9:
            child=read(1)[0];count=struct.unpack('>i',read(4))[0]
            if not 0<=count<=10:raise ValueError('Unexpected list bound')
            return [payload(child) for _ in range(count)]
        if kind==10:
            result={}
            while True:
                child=read(1)[0]
                if child==0:return result
                name=text()
                if name in result:raise ValueError('Duplicate NBT key')
                result[name]=payload(child)
        raise ValueError('Unexpected NBT type '+str(kind))
    kind=read(1)[0]
    if kind!=10 or text()!='':raise ValueError('Expected anonymous compound root')
    result=payload(kind)
    if stream.read(1):raise ValueError('Trailing NBT data')
    return result


class PublicPrismJoinTests(unittest.TestCase):
    def test_fresh_native_server_list_has_public_and_local_choices(self):
        data=decode_nbt(server_list())
        self.assertEqual(set(data),{'servers'})
        public,local=data['servers']
        self.assertEqual(public['ip'],PUBLIC_SERVER)
        self.assertEqual(local['ip'],LOCAL_SERVER)
        self.assertIn('Public',public['name'])
        self.assertIn('local computer only',local['name'])
        for row in data['servers']:
            self.assertEqual(set(row),{'name','ip','hidden'})
            self.assertEqual(row['hidden'],0)
            self.assertNotIn('acceptTextures',row)

    def test_primary_join_uses_visible_native_multiplayer_action(self):
        title=(REPO/'packwiz/config/fancymenu/customization/awft_title.txt').read_text()
        blocks=re.findall(r'(\w+)\s*\{([^{}]*)\}',title)
        primary=[(kind,body) for kind,body in blocks if 'label = Join Our World\n' in body]
        self.assertEqual(len(primary),1)
        kind,body=primary[0]
        self.assertEqual(kind,'vanilla_button')
        self.assertIn('element_type = vanilla_button',body)
        self.assertIn('is_hidden = false',body)
        self.assertIn('instance_identifier = mc_titlescreen_multiplayer_button',body)
        self.assertEqual(title.count('instance_identifier = mc_titlescreen_multiplayer_button'),1)
        self.assertNotIn('[action_type:joinserver]',title)
        self.assertNotIn('127.0.0.1',title)


if __name__=='__main__':unittest.main()
