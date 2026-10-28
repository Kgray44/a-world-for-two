"""Small source-contract checks; native appearance/use is independently pending."""
import unittest
from unittest.mock import patch

from control_room.common import UserError
from tools.artistic_tortuga_pair import AIR, admitted_before, merchant, smith, validate


def literal(registry, name, **props):
    # Geometry isolation only. prepare() separately resolved every real state
    # against the actual exported native registry before producing its bundle.
    values={k:str(v).lower() if isinstance(v,bool) else str(v) for k,v in props.items()}
    return name+('['+','.join(k+'='+v for k,v in sorted(values.items()))+']' if values else '')


class TortugaPairTests(unittest.TestCase):
    def test_two_real_doors_survive_route_reservation_and_stairs_have_clear_heads(self):
        registry={'items':['minecraft:'+s for s in ('coal','iron_ingot','leather','paper','string','white_wool','bread')]}
        with patch('tools.artistic_tortuga_pair.state',side_effect=literal):
            for builder in (smith,merchant):
                p=builder(registry);validate(p)
                for entry in p.entries:
                    x,y,z=entry['local']
                    original=[p.blocks[x,y+d,z] for d in (0,1)]
                    p.reserve('route repeated across openable door',[(x,y,z)])
                    self.assertEqual(original,[p.blocks[x,y+d,z] for d in (0,1)])
                x,y,z=p.stairs[2];p.blocks[x,y+1,z]='minecraft:stone'
                with self.assertRaisesRegex(UserError,'staircase'):
                    validate(p)

    def test_a_dry_one_block_shoe_is_not_permission_for_water_or_old_storage(self):
        pos=(1013,63,-1284)
        admitted_before(pos,AIR,True,'minecraft:gravel',False)
        for old,below,protected in ((AIR,'minecraft:water[level=0]',False),
                ('minecraft:barrel','minecraft:gravel',False),(AIR,'minecraft:gravel',True)):
            with self.subTest(old=old,below=below,protected=protected),self.assertRaises(UserError):
                admitted_before(pos,old,True,below,protected)


if __name__=='__main__':
    unittest.main()
