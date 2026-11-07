from datetime import datetime,timezone,timedelta
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('rose_dashboard',Path(__file__).resolve().parents[1]/'dashboard.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class DashboardTests(unittest.TestCase):
    def test_fresh_controls_are_narrow_and_not_runtime_acknowledgements(self):
        with tempfile.TemporaryDirectory()as temp:
            calls=[];t=module.Tavern(temp,lambda *a,**k:calls.append((a,k)))
            t.path.parent.mkdir(parents=True)
            row={'at':datetime.now(timezone.utc).isoformat(),'residents':[{'id':'ada-brine'}]}
            t.path.write_text(json.dumps(row))
            result=t.control({'action':'enabled','id':'ada-brine','enabled':False})
            self.assertFalse(result['runtime_acknowledged']);self.assertEqual('awfttavern resident ada-brine enabled false',calls[0][0][0])
            for body in [{'action':'enabled','id':'ada-brine\nstop','enabled':True},
                         {'action':'music','enabled':'false'},
                         {'action':'weight','id':'ada-brine','activity':'social','weight':True},
                         {'action':'initialize'}]:
                with self.assertRaises(ValueError):t.control(body)
            self.assertEqual(1,len(calls))
            row['at']=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat();t.path.write_text(json.dumps(row))
            with self.assertRaises(ValueError):t.control({'action':'music','enabled':False})
            self.assertEqual(1,len(calls))
