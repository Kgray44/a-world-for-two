"""Runs the real proposed wrapper preflight without a console or world call."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util,json,tempfile,unittest
from unittest.mock import patch
from tools import artistic_review as review
class ReachedWrite(Exception):pass
class LiveOrdinaryPreflight(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  root=Path(self.temp.name);home=root/'owned'/'world-test'/'home';home.mkdir(parents=True)
  self.layout=SimpleNamespace(home=home,state=home/'dashboard',world=home/'world')
  self.path=home/'source.json';self.backup='a'*64
  self.plan={'world_path':str(home/'world'/'RosewaterArtistic'),'backup_sha256':self.backup,'bounds':[0,0,255,0],
   'blocks':[[n,64,0,0] for n in range(256)],'palette':['minecraft:stone'],'commands':[],'block_entities':[],
   'live_ordinary':True,'live_policy_sha256':'b'*64}
 def run_plan(self,plan,*,online=True,prefix='awftbuild place '):
  self.path.write_text(json.dumps(plan));command=prefix+__import__('hashlib').sha256(self.path.read_bytes()).hexdigest()
  metrics={'players':{'KG':{}},'bridge_age_seconds':0} if online else {'players':{},'bridge_age_seconds':0}
  def request(home,route,*args):
   if route=='metrics':return metrics
   if route=='overview':return {'server':{'state':'online','status':{'players':{'online':1 if online else 0}}}}
   raise AssertionError('No console/native action allowed in this fixture')
  with patch.object(review,'Layout',return_value=self.layout),patch.object(review,'request',side_effect=request),patch.object(review,'read_json',return_value={'sha256':self.backup}),patch.object(review,'atomic_write',side_effect=ReachedWrite):
   return review.native(self.layout.home,command,plan_path=self.path)
 def test_exact256_live_preflight_reaches_owned_stage_only(self):
  with self.assertRaises(ReachedWrite):self.run_plan(self.plan)
 def test257_denied_before_console_or_stage(self):
  self.plan['blocks'].append([256,64,0,0])
  with self.assertRaises(review.UserError):self.run_plan(self.plan)
 def test_BE_commands_invalid_hash_not_online_optins(self):
  for key,value in [('commands',['say unsafe']),('block_entities',[{'pos':[0,64,0],'nbt':'{}'}]),('live_policy_sha256','z'*64),('live_ordinary',False)]:
   plan=self.plan|{key:value}
   with self.subTest(key=key),self.assertRaises(review.UserError):self.run_plan(plan)
 def test_live_oversize_before_decode(self):
  self.plan['untrusted_padding']='x'*66000
  with self.assertRaisesRegex(review.UserError,'64KiB'):self.run_plan(self.plan)
 def test_empty_server_offline_mode_preserved(self):
  self.plan['live_ordinary']=False
  with self.assertRaises(ReachedWrite):self.run_plan(self.plan,online=False)
 def test_missing_optin_is_offline_and_denied_with_real_roster(self):
  self.plan.pop('live_ordinary')
  with self.assertRaises(review.UserError):self.run_plan(self.plan)
  with self.assertRaises(ReachedWrite):self.run_plan(self.plan,online=False)
 def test_engineering_never_inherits_live_ordinary_optin(self):
  with self.assertRaises(review.UserError):self.run_plan(self.plan,prefix='awftengine setup ')
if __name__=='__main__':unittest.main(verbosity=2)
