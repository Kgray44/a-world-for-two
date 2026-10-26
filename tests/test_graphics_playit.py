import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_room.common import Layout, UserError, atomic_write, digest, write_json
from control_room.graphics import Graphics
from control_room.playit import Playit, public_text, safe_snapshot
from tools.prism_export import command


class GraphicsAndPlayitTests(unittest.TestCase):
    def test_prism_command_runs_bootstrap_with_a_pinned_main_jar_and_safe_url(self):
        text=command('https://kgray44.github.io/a-world-for-two/pack.toml')
        self.assertIn('-jar "$INST_MC_DIR/awft-tools/packwiz-installer-bootstrap-v0.0.3.jar"',text)
        self.assertIn('--bootstrap-main-jar "$INST_MC_DIR/awft-tools/packwiz-installer-v0.5.14.jar"',text)
        for url in ('http://127.0.0.1/pack.toml','https://elsewhere.invalid/a-world-for-two/pack.toml',
                    'https://kgray44.github.io/a-world-for-two/x;command/pack.toml'):
            with self.assertRaises(UserError):command(url)

    def test_playit_protocol_hello_and_snapshot_drop_private_account_data(self):
        agent = Playit()
        agent._accept({'message_kind':'hello','data':{'protocol':{'ipc_version':2}}})
        agent._accept({'message_kind':'response','data':{'ipc_version':2,'response':{'type':'subscribe','data':{'snapshot':{
            'status':{'phase':'running','has_secret':True,'secret_path':'private-path','version':'1.0.10'},
            'lifecycle':{'state':'running','data':{'login_link':'private-login','agent_id':'private-id','tunnels':[
                {'display_address':'example.ply.gg','destination':'127.0.0.1:25565','secret':'private-key'}]}},
            'stats':{'active_tcp':0,'bytes_in':123,'secret':'private-stats'}}}}}})
        data=safe_snapshot(agent._status,agent._lifecycle,agent._stats)
        self.assertTrue(data['linked'])
        self.assertEqual(data['tunnels'][0]['destination'],'127.0.0.1:25565')
        self.assertNotIn('private-',json.dumps(data))

    def test_playit_refuses_unknown_protocol_and_service_actions(self):
        agent=Playit()
        with self.assertRaises(ValueError):agent._accept({'message_kind':'hello','data':{'protocol':{'ipc_version':99}}})
        with patch('control_room.playit.subprocess.run') as command:
            with self.assertRaises(UserError):agent.action('reset',True)
            with self.assertRaises(UserError):agent.action('stop',False)
            command.assert_not_called()

    def test_playit_activity_redacts_auth_links_and_credentials(self):
        text=public_text('secret=abc token:xyz https://playit.gg/claim/private-token '+'a'*64)
        for secret in ('abc','xyz','private-token','a'*64):self.assertNotIn(secret,text)

    def test_shader_change_requires_current_revision_and_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            layout=Layout(Path(directory));layout.create()
            instance=layout.home/'instances/AWFT_Check_20261026_214756'
            write_json(instance/'awft-owned.json',{'format':'awft-owned-client:1','root':str(instance)})
            iris=instance/'.minecraft/config/iris.properties'
            atomic_write(iris,'enableShaders=true\nshaderPack=owner-choice.zip\ncustom=value\n')
            storage=type('Storage',(),{'reserve':lambda *args:None})()
            graphics=Graphics(layout,storage)
            with patch('control_room.graphics.closed'):
                with self.assertRaises(UserError):graphics.apply(instance.name,'off','stale')
                self.assertIn('enableShaders=true',iris.read_text())
                result=graphics.apply(instance.name,'off',digest(iris))
            self.assertIn('enableShaders=false',iris.read_text())
            self.assertIn('shaderPack=owner-choice.zip',iris.read_text())
            self.assertIn('custom=value',iris.read_text())
            self.assertTrue(Path(result['previous']).is_file())


if __name__=='__main__':unittest.main()
