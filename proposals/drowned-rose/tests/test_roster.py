import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rose_prepare',HERE/'prepare.py')
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)


class RosterTests(unittest.TestCase):
    def test_complete_independent_residents(self):
        rows=prepare.roster()
        self.assertEqual(45,len(rows));self.assertEqual(45,len({r['id']for r in rows}));self.assertEqual(45,len({r['name']for r in rows}))
        lines=[line for row in rows for line in row['dialogue']]
        self.assertEqual(360,len(lines));self.assertEqual(360,len(set(lines)))
        ids={r['id']for r in rows}
        for row in rows:
            self.assertEqual(8,len(row['dialogue']))
            self.assertTrue(set(row['social_preferences'])<=ids)
            self.assertNotIn(row['id'],row['social_preferences'])
            self.assertTrue(all(1<=w<=12 for w in row['preferences'].values()))
            self.assertTrue({'sit','walk','social','watch','window','bar'}<=row['preferences'].keys())
            self.assertNotIn('bed',row);self.assertNotIn('profession',row)


if __name__=='__main__':unittest.main()
