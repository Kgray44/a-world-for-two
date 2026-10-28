"""True source-preservation gates; not native POI or resident acceptance."""
import importlib.util
from pathlib import Path
import unittest

from control_room.common import UserError

spec=importlib.util.spec_from_file_location('awft_town_life_pilot',Path(__file__).parents[1]/'compat/control-bridge/proposals/life-extension/town-pilot/prepare.py')
pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)


class TownPilot(unittest.TestCase):
    def field(self):
        field={q:'minecraft:air' for q in pilot.BED}
        field.update({(x,y-1,z):'minecraft:oak_planks' for x,y,z in pilot.BED})
        return field
    def test_real_bed_uses_only_two_unused_authored_air_cells(self):
        source=self.field();self.assertEqual(pilot.bed_delta(source,source),pilot.BED)
        self.assertEqual(sum('part=head' in v for v in pilot.BED.values()),1)
        self.assertEqual(sum('part=foot' in v for v in pilot.BED.values()),1)
    def test_old_furnishing_is_not_replaced_for_a_poi(self):
        source=self.field();actual=dict(source);actual[next(iter(pilot.BED))]='minecraft:chest'
        with self.assertRaises(UserError):pilot.bed_delta(source,actual)
    def test_a_saved_be_is_never_reloaded_or_discarded(self):
        source=self.field()
        with self.assertRaises(UserError):pilot.bed_delta(source,source,[next(iter(pilot.BED))])
    def test_changed_floor_refuses_the_addition(self):
        source=self.field();actual=dict(source);x,y,z=next(iter(pilot.BED));actual[x,y-1,z]='minecraft:air'
        with self.assertRaises(UserError):pilot.bed_delta(source,actual)
    def test_flat_routes_start_at_each_real_footing_and_do_not_teleport(self):
        for row in pilot.proposals():
            start=tuple(int(v//1) for v in row['feet'])
            for key in ('shelter_path','bed_path','job_path'):
                route=row['habitat'].get(key)
                if not route:continue
                self.assertEqual(tuple(route[0]),start)
                for a,b in zip(route,route[1:]):
                    self.assertEqual(a[1],b[1]);self.assertEqual(abs(a[0]-b[0])+abs(a[2]-b[2]),1)


if __name__=='__main__':unittest.main()
