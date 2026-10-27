import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_grounds import construct,check


class SavedGround:
    def __init__(self,overrides=None):self.overrides=overrides or {};self.protected=set()
    def state(self,p):return self.overrides.get(p,'minecraft:grass_block[snowy=false]' if p[1]==63 else 'minecraft:dirt' if p[1]<63 else 'minecraft:air')


class NorthernGroundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.registry=json.loads((Path(__file__).parent/'fixtures/artistic_street_registry.json').read_text())
    def plan(self,pos,state):
        return {'world_path':self.registry['world_path'],'seed':self.registry['seed'],'palette':[state],'blocks':[[*pos,0]],'block_entities':[]}

    def test_connected_small_grounds_obey_outdoor_nine_rule(self):
        p=construct(self.registry,SavedGround(),[]);result=check(p)
        self.assertTrue(result['connected']);self.assertTrue(result['all_authored_runs_at_most_nine'])
        self.assertLess(len(p.blocks),4096);self.assertEqual(2,len(p.tags))

    def test_existing_authored_paving_is_adopted_never_replaced(self):
        pos=(1193,64,-1203);plan=self.plan(pos,'minecraft:stone_bricks')
        p=construct(self.registry,SavedGround({pos:'minecraft:stone_bricks'}),[('old paving',plan,'a'*64)])
        self.assertNotIn(pos,p.blocks);self.assertEqual('minecraft:stone_bricks',p.adopted[pos])

    def test_water_refuses_and_changed_authored_air_is_identified(self):
        with self.assertRaisesRegex(UserError,'wet'):
            construct(self.registry,SavedGround({(1202,63,-1213):'minecraft:water[level=0]'}),[])
        pos=(1193,64,-1203);plan=self.plan(pos,'minecraft:air')
        p=construct(self.registry,SavedGround(),[('old clearance',plan,'b'*64)])
        self.assertIn(pos,p.required_air)


if __name__=='__main__':unittest.main()
