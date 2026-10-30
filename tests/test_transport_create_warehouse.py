"""Native lane connectivity and inventory-preserving refusal checks."""
import json
import unittest

from control_room.common import UserError
from tests.test_transport_create_shops import SCHEMAS, fixture
from tools import transport_create_warehouse as lane
from tools import transport_create_shops as shops
from tools import transport_create_continuous as motor


class WarehouseSourceTests(unittest.TestCase):
    def setUp(self):
        self.registry = {'seed': 7, 'world_path': 'D:/test/world', 'blocks': {
            **SCHEMAS,
            'overpressure:pneumatic_connection': {'facing': ['north', 'east', 'south', 'west', 'up', 'down'],
                'arrow_facing': ['north', 'east', 'south', 'west'], 'mode': ['extract', 'insert', 'disabled'], 'powered': ['false', 'true']},
            'overpressure:item_pump': {'facing': ['north', 'east', 'south', 'west', 'up', 'down'], 'waterlogged': ['false', 'true']},
            'overpressure:pneumatic_tube': {**{k: ['false', 'true'] for k in
                ('north', 'east', 'south', 'west', 'up', 'down', 'has_connection', 'has_rim', 'has_second_rim', 'waterlogged')},
                'rim': ['north', 'east', 'south', 'west', 'up', 'down']},
        }}
        self.spec = lane.specification(self.registry)
        self.source, self.actual = fixture(self.spec)

    def derive(self, actual=None, protected=()):
        return shops.derive(self.registry, 'warehouse', self.spec, self.source,
                            self.actual if actual is None else actual, protected, 'a'*64)

    def test_connected_real_item_lane_and_side_cog_leave_crank_pipe_ports_separate(self):
        nodes = (lane.INPUT, lane.EXTRACT, lane.PUMP, lane.TUBE, lane.INSERT, lane.OUTPUT)
        for a, b in zip(nodes, nodes[1:]):
            self.assertEqual(sum(abs(a[i]-b[i]) for i in range(3)), 1)
            self.assertEqual(a[0]-b[0], 1)
        self.assertEqual(lane.COG, (lane.PUMP[0], lane.PUMP[1], lane.PUMP[2]+1))
        self.assertEqual(lane.CRANK, (lane.COG[0]+1, lane.COG[1], lane.COG[2]))
        self.assertNotIn(lane.CRANK, nodes)
        tube = shops.key(self.spec['blocks'][lane.TUBE])
        self.assertEqual(tube, 'overpressure:pneumatic_tube')
        self.assertIn('has_rim=true', self.spec['blocks'][lane.TUBE])
        self.assertIn('rim=west', self.spec['blocks'][lane.TUBE])

    def test_eight_new_cells_are_disjoint_from_first_shops_and_continuous_dry_cells(self):
        cells = set(self.spec['blocks'])
        self.assertEqual(len(cells), 8)
        first = {q for s in shops.shops(self.registry).values() for q in s['blocks']}
        self.assertFalse(cells & first)
        # The entire continuous motor enclosure/drive reserve is well away.
        self.assertTrue(all(q[2] > max(p[2] for p in motor.INTERIOR) for q in cells))

    def test_no_goods_filter_template_or_current_inventory_are_authored(self):
        docs = self.derive()
        for name, raw in docs.items():
            v = json.loads(raw)
            self.assertEqual(v['block_entities'], [])
            self.assertEqual(v['commands'], [])
            self.assertEqual(v['construction_forbidden'], name != 'additions-PROPOSAL.json')
        proposal = json.loads(docs['additions-PROPOSAL.json'])
        self.assertEqual(len(proposal['blocks']), 8)
        self.assertNotIn('filter', proposal)

    def test_current_container_or_air_named_be_is_a_refusal_not_recreated_stock(self):
        for q in (lane.INPUT, lane.OUTPUT, lane.PUMP, lane.TUBE):
            changed = dict(self.actual)
            changed[q] = 'minecraft:barrel[facing=up,open=false]'
            with self.assertRaises(UserError):
                self.derive(changed)
            with self.assertRaises(UserError):
                self.derive(protected=[q])


if __name__ == '__main__':
    unittest.main()
