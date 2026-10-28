"""Coverage diagnostics preserve holes, coast gaps and actual-source meaning."""
import hashlib,json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from control_room.common import UserError
from tools.artistic_west_coverage import components,largest_rectangle,actual_geometry


class WesternCoverageTests(unittest.TestCase):
    def test_components_do_not_bridge_unknown_or_water_gaps(self):
        land={(x,z)for x in range(9)for z in range(3)if x!=4}
        islands=components(land)
        self.assertEqual([len(r)for r in islands],[12,12])
        self.assertFalse(islands[0]&islands[1])
        land.add((4,1))
        self.assertEqual([len(r)for r in components(land)],[25])

    def test_empty_patch_rectangle_does_not_cover_cropped_wet_corner(self):
        land={(x,z)for x in range(10)for z in range(6)}
        land-={(x,z)for x in range(6,10)for z in range(3,6)}
        rect=largest_rectangle(land)
        self.assertEqual(rect['area_columns'],36)
        x0,z0,x1,z1=rect['bounds_xz']
        self.assertTrue({(x,z)for x in range(x0,x1+1)for z in range(z0,z1+1)}<=land)
        self.assertIsNone(largest_rectangle(set()))

    def test_reservation_air_never_counts_as_physical_main_floor(self):
        with TemporaryDirectory()as folder:
            root=Path(folder);name='future-reservation-ONLY.json'
            raw=json.dumps({'palette':['minecraft:air'],'blocks':[[0,63,0,0]],'construction_forbidden':True}).encode()
            (root/name).write_bytes(raw)
            manifest={'files':{name:{'sha256':hashlib.sha256(raw).hexdigest()}}}
            raw=json.dumps(manifest).encode();(root/'manifest.json').write_bytes(raw)
            with patch('tools.artistic_west_coverage.MANIFEST_PINS',{'manifest.json':hashlib.sha256(raw).hexdigest()}):
                with self.assertRaisesRegex(UserError,'mask is not physical geometry'):
                    actual_geometry(root,'manifest.json',name)


if __name__=='__main__':unittest.main()
