"""Real loopback HTTP/filesystem checks; Minecraft is never launched by these tests."""
from __future__ import annotations

import copy
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from control_room.backups import Backups
from control_room.character_atlas import markers
from control_room.characters import Characters
from control_room.common import Layout, UserError, read_json, write_json
from control_room.jobs import Jobs
from control_room.web import Application, HTTPServer, make_handler


class ReservedFixtureStorage:
    def reserve(self, size, target=None):
        if type(size) is not int or not 0 <= size <= 128*1024**2:
            raise AssertionError('Test allocation exceeds its bound')
    checkpoint = reserve


class CharacterHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='awft-character-http-')
        self.layout = Layout(Path(self.temp.name))
        self.layout.create()
        self.storage = ReservedFixtureStorage()
        with patch('control_room.web.Storage', return_value=self.storage):
            self.app = Application(self.layout.home)
        self.service = self.app.characters
        self.app.atlas = SimpleNamespace(snapshot=lambda: {'waypoints': [], 'locations': []}, close=lambda:None)
        self.http = HTTPServer(('127.0.0.1', 0), make_handler(self.app))
        self.port = self.http.server_port
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(2)
        self.app.jobs.close()
        self.service.close()
        self.app.close()
        for handler in list(self.app.error_logger.handlers):
            handler.close()
            self.app.error_logger.removeHandler(handler)
        self.temp.cleanup()

    def request(self, path, body=None, csrf=True):
        headers = {'Origin': 'http://127.0.0.1:'+str(self.port)}
        if csrf:
            headers['X-AWFT-CSRF'] = self.app.token
        if body is not None:
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request('http://127.0.0.1:'+str(self.port)+path,
            data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with urllib.request.urlopen(request, timeout=4) as response:
            raw=response.read(1024**2)
            return json.loads(raw) if response.headers.get_content_type()=='application/json' else raw

    def test_real_http_save_reload_stage_and_stale_edit_preservation(self):
        detail = self.request('/api/characters/detail?id=barnacle-bill')
        profile = detail['character']
        profile['personality']['speaking_style'] = 'Quiet nautical understatement.'
        saved = self.request('/api/characters/save', {'profile': profile, 'expected': detail['revision']})
        self.assertEqual(Characters(self.layout,self.storage).detail(profile['id'])['character']['personality']['speaking_style'], 'Quiet nautical understatement.')
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/characters/save', {'profile': profile, 'expected': detail['revision']})
        self.assertEqual(error.exception.code,400)
        staged = self.request('/api/characters/apply', {'expected': saved['revision']})
        self.assertFalse(staged['acknowledged'])
        self.assertEqual(read_json(self.service.folder/'runtime.json')['characters'][0]['personality']['speaking_style'], 'Quiet nautical understatement.')
        self.assertFalse((self.layout.server/'config/awft-living-world.json').exists())

    def test_loopback_preview_job_returns_saved_scripted_dialogue(self):
        detail = self.request('/api/characters/detail?id=barnacle-bill')
        profile=detail['character']
        profile['dialogue']['lines']['greetings']=['The soup has requested shore leave.']
        self.request('/api/characters/save', {'profile':profile,'expected':detail['revision']})
        ticket=self.request('/api/characters/preview', {'id':profile['id'],'message':'Hello, Bill!'})
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            job=next(x for x in self.request('/api/jobs') if x['id']==ticket['job'])
            if job['status'] in ('complete','failed'):
                break
            time.sleep(.01)
        self.assertEqual(job['status'],'complete',job)
        self.assertEqual(job['result']['mode'],'scripted')
        self.assertIn('shore leave',job['result']['response'])

    def test_http_auth_static_assets_and_atlas_hook(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/characters/apply',{},csrf=False)
        self.assertEqual(error.exception.code,403)
        self.assertIn(b'mountCharacters',self.request('/characters.js'))
        self.assertIn(b'character-studio',self.request('/characters.css'))
        atlas=self.request('/api/atlas')
        self.assertEqual(atlas['characters'],[])


class CharacterBackupTests(unittest.TestCase):
    def test_profile_backup_restore_preserves_the_replaced_registry(self):
        with tempfile.TemporaryDirectory(prefix='awft-character-backup-') as directory:
            layout=Layout(Path(directory));layout.create();storage=ReservedFixtureStorage()
            world=layout.world/'Synthetic';world.mkdir();(world/'level.dat').write_bytes(b'SYNTHETIC')
            service=Characters(layout,storage);detail=service.detail('barnacle-bill')
            service.save(detail['character'],detail['revision'])
            original=service.path.read_bytes()
            backup=Backups(layout,storage,SimpleNamespace(running=lambda:False))
            receipt=backup.create()
            profile=service.detail('barnacle-bill');profile['character']['nickname']='Newer unique edit'
            service.save(profile['character'],profile['revision']);newer=service.path.read_bytes()
            restored=backup.restore(receipt['id'],'RESTORE '+receipt['id'])
            self.assertEqual(service.path.read_bytes(),original)
            self.assertEqual((Path(restored['previous_world'])/'characters/registry.json').read_bytes(),newer)
            self.assertEqual(Characters(layout,storage).detail('barnacle-bill')['character']['nickname'],'')


class CharacterAtlasTests(unittest.TestCase):
    def test_assigned_and_expired_positions_never_claim_live(self):
        now=datetime.now(timezone.utc).timestamp()
        profile={'id':'bill','kind':'villager','name':'Bill','district':'tortuga',
                 'location':{'x':1,'y':64,'z':2,'dimension':'minecraft:overworld','status':'live',
                             'measured_at':datetime.fromtimestamp(now-90,timezone.utc).isoformat()}}
        self.assertEqual(markers([profile],now)[0]['state'],'last known')
        profile['location']['status']='assigned';profile['location']['measured_at']=None
        self.assertEqual(markers([profile],now)[0]['state'],'assigned home')
        profile['location']['x']=None
        self.assertEqual(markers([profile],now),[])


if __name__=='__main__':
    unittest.main()
