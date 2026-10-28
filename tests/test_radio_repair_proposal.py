"""Execute the proposed real dispatcher method only; no server/world actions."""
import ast
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from control_room.common import Layout, UserError, write_json
from control_room import server as module

ROOT=Path(__file__).resolve().parents[1]
PROPOSAL=ROOT/'compat/proposals/bridge-radio-readiness-r1'


class RadioRepairDispatch(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='awft-radio-repair-source-')
        self.addCleanup(self.temp.cleanup)
        self.layout=Layout(Path(self.temp.name));self.layout.create()
        self.server=module.Server(self.layout,object())
        tree=ast.parse((PROPOSAL/'server.py.proposed').read_text(encoding='utf-8'))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Server')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='command')
        scope=vars(module).copy()
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<proposed-command>','exec'),scope)
        self.server.command=types.MethodType(scope['command'],self.server)
        self.command='awftengine repair-radio '+'a'*64

    def private(self):
        write_json(self.layout.state/'artistic-owner.json',{'format':'awft-artistic-stage:1','home':str(self.layout.home)})
        self.layout.save_settings(self.layout.settings()|{'permanent_world':False,'port':25575})

    def test_exact_private_command_requires_confirmation(self):
        self.private()
        with patch.object(self.server,'_write') as write:
            with self.assertRaisesRegex(UserError,'Confirm'):
                self.server.command(self.command)
            self.server.command(self.command,confirmed=True)
            write.assert_called_once_with(self.command)

    def test_foreign_permanent_or_wrong_port_never_dispatches(self):
        with patch.object(self.server,'_write') as write:
            with self.assertRaises(UserError):self.server.command(self.command,confirmed=True)
            for change in ({'permanent_world':True},{'port':25565}):
                self.private();self.layout.save_settings(self.layout.settings()|change)
                with self.assertRaises(UserError):self.server.command(self.command,confirmed=True)
            self.private()
            write_json(self.layout.state/'artistic-owner.json',{'format':'awft-artistic-stage:1','home':str(self.layout.home/'other')})
            with self.assertRaises(UserError):self.server.command(self.command,confirmed=True)
            write.assert_not_called()

    def test_no_extra_arguments_invalid_hash_or_command_injection(self):
        self.private()
        with patch.object(self.server,'_write') as write:
            for bad in (self.command+' extra',self.command.replace('a'*64,'b'*63),self.command+'\nstop',
                        self.command.replace('repair-radio','repair-radio-all')):
                with self.subTest(command=bad),self.assertRaises(UserError):
                    self.server.command(bad,confirmed=True)
            write.assert_not_called()

    def test_repair_cannot_enter_setup_or_button_branch(self):
        source=(PROPOSAL/'EngineeringSupport.java').read_text(encoding='utf-8')
        begin=source.index('if(mode.equals("repair-radio")){',source.index('if(readySamples<2)'))
        end=source.index('else if(mode.equals("setup"))',begin)
        branch=source[begin:end]
        self.assertIn('reattachMissingReceiversOnce()',branch)
        self.assertNotIn('pulse(',branch)
        self.assertNotIn('configureRadios()',branch)
        self.assertIn('if(mode.equals("repair-radio"))throw new IllegalStateException("Lifecycle repair can NEVER press a button")',source)


if __name__=='__main__':unittest.main()
