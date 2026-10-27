"""Public/local join regressions; native client import is a separate receipt."""
import io
import copy
import hashlib
import json
import re
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from control_room.common import REPO, UserError
from tools import prism_export as export
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


class PirateModpackInclusionTests(unittest.TestCase):
    """Synthetic archive custody, with no third-party artifact stored in the tests."""
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='awft-export-test-')
        self.addCleanup(temporary.cleanup)
        self.repo=Path(temporary.name)
        notice=self.repo/'docs/PIRATE-MODPACK-PERMISSION.md'
        notice.parent.mkdir();notice.write_text('Reviewed synthetic notice\n',encoding='utf-8')
        self.raw=b'synthetic unchanged pirate fixture'
        approved=dict(export.PIRATE_PIN,size=len(self.raw))
        self.pin=approved|{'hashes':{'sha256':hashlib.sha256(self.raw).hexdigest()},
                            'kind':'mod','side':'both','optional':False,'default':True}
        for target,value in [('REPO',self.repo),('PIRATE_PIN',approved),('PIRATE_SHA256',self.pin['hashes']['sha256'])]:
            mock=patch.object(export,target,value);mock.start();self.addCleanup(mock.stop)

    def archive(self,*,jar=None,notice=None,extra_mod=False,metadata=True):
        title=('vanilla_button {\nlabel = Join Our World\nhoverlabel = Join Our World\n'
               'is_hidden = false\ninstance_identifier = mc_titlescreen_multiplayer_button\n}\n')
        files={'config/fancymenu/assets/awft-background.png':b'artwork',
               'config/fancymenu/customization/awft_title.txt':title.encode(),
               'config/iris.properties':b'enableShaders=false\n'}
        for name,raw in files.items():
            path=self.repo/'packwiz'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        tools=[]
        for filename,raw in [('packwiz-installer-bootstrap-v0.0.3.jar',b'bootstrap'),('packwiz-installer-v0.5.14.jar',b'full')]:
            tools.append({'filename':filename,'size':len(raw),'hashes':{'sha256':hashlib.sha256(raw).hexdigest()},'fixture':raw})
        prelaunch=export.command('https://kgray44.github.io/a-world-for-two/releases/0.1.0-candidate.23/pack.toml')
        result=io.BytesIO()
        with zipfile.ZipFile(result,'w') as archive:
            archive.writestr('instance.cfg','PreLaunchCommand='+prelaunch.replace('"','\\"')+'\nMaxMemAlloc=6144\nOverrideJavaLocation=false\n')
            archive.writestr('mmc-pack.json',json.dumps({'components':[{'uid':'net.neoforged','version':'21.1.262'}]}))
            for name in ('INSTALL.txt','CONNECT.txt','.minecraft/options.txt','.minecraft/awft-tools/LICENSE.txt'):
                archive.writestr(name,'synthetic fixture')
            archive.writestr('.minecraft/servers.dat',export.server_list())
            for pin in tools:archive.writestr('.minecraft/awft-tools/'+pin['filename'],pin['fixture'])
            for name,raw in files.items():archive.writestr('.minecraft/'+name,raw)
            archive.writestr('.minecraft/mods/'+self.pin['filename'],self.raw if jar is None else jar)
            archive.writestr(export.PIRATE_NOTICE,(self.repo/'docs/PIRATE-MODPACK-PERMISSION.md').read_bytes() if notice is None else notice)
            included={'slug':self.pin['slug'],'filename':self.pin['filename'],'size':self.pin['size'],
                      'sha256':self.pin['hashes']['sha256'],'permission_url':export.PIRATE_GRANT_URL,'notice':export.PIRATE_NOTICE}
            archive.writestr('awft-export.json',json.dumps({'modpack_bundled_artifacts':[included] if metadata else []}))
            if extra_mod:archive.writestr('.minecraft/mods/unreviewed.jar',b'not allowed')
        result.seek(0)
        return result,prelaunch,tools,{'sha256':hashlib.sha256(b'artwork').hexdigest()}

    def test_exact_one_reviewed_file_and_notice_pass(self):
        archive,command,tools,artwork=self.archive()
        checks=export.verify_archive(archive,command,tools,artwork,self.pin)
        self.assertEqual(checks['bundled_third_party_mod_jars'],1)
        self.assertEqual(checks['approved_modpack_jar_identity'],'pass')
        self.assertEqual(checks['modpack_permission_notice'],'pass')

    def test_changed_jar_same_size_fails_hash(self):
        archive,command,tools,artwork=self.archive(jar=b'X'+self.raw[1:])
        with self.assertRaisesRegex(UserError,'JAR changed'):
            export.verify_archive(archive,command,tools,artwork,self.pin)

    def test_notice_cannot_be_replaced(self):
        archive,command,tools,artwork=self.archive(notice=b'no permission')
        with self.assertRaisesRegex(UserError,'permission notice'):
            export.verify_archive(archive,command,tools,artwork,self.pin)

    def test_second_gameplay_jar_is_rejected(self):
        archive,command,tools,artwork=self.archive(extra_mod=True)
        with self.assertRaisesRegex(UserError,'unexpected or unsafe'):
            export.verify_archive(archive,command,tools,artwork,self.pin)

    def test_export_metadata_must_disclose_the_bundled_file(self):
        archive,command,tools,artwork=self.archive(metadata=False)
        with self.assertRaisesRegex(UserError,'single author-permitted'):
            export.verify_archive(archive,command,tools,artwork,self.pin)

    def test_missing_or_duplicate_lock_entries_fail(self):
        for rows in ([],[self.pin,self.pin]):
            with self.subTest(count=len(rows)),self.assertRaisesRegex(UserError,'Exactly one'):
                export.approved_pirate({'mods':rows})

    def test_changed_lock_pin_or_role_requires_fresh_review(self):
        for key,value in [('size',self.pin['size']+1),('curseforge_file',123),('provider','other'),
                          ('side','client'),('optional',True),('default',False)]:
            changed=copy.deepcopy(self.pin);changed[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(UserError,'review the exact file'):
                export.approved_pirate({'mods':[changed]})
        changed=copy.deepcopy(self.pin);changed['hashes']['sha256']='0'*64
        with self.assertRaisesRegex(UserError,'review the exact file'):
            export.approved_pirate({'mods':[changed]})


if __name__=='__main__':unittest.main()
