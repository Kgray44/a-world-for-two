from pathlib import Path
import hashlib
import unittest
from tools.artistic_life_scale_proposal import BASE,transform


class LifeScaleProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[1];folder=root/'compat/proposals/life-scale49'
        cls.base=(folder/'NativeHabitatLifeSupport48-diagnostic-base.java.txt').read_text()
        cls.source=(folder/'NativeHabitatLifeSupport.java').read_text()
        cls.policy=(root/'compat/control-bridge/src/worldfortwo/bridge/HabitatLifePolicy.java').read_text()

    def test_exact_frozen_diagnostic_base_and_full_deterministic_derivation(self):
        self.assertEqual(BASE,hashlib.sha256(self.base.encode()).hexdigest())
        self.assertEqual(transform(self.base),self.source)

    def test_legacy_policy64_and_factory_spawn_ai_guards_are_unmodified(self):
        self.assertIn('WORLD_POPULATION_CAP=64',self.policy)
        a='    private void flags(';b='    private Map<String,Object> observation('
        proposed=self.source[self.source.index(a):self.source.index(b)].replace('        scaledCrowding(row);\n','')
        self.assertEqual(self.base[self.base.index(a):self.base.index(b)],proposed)
        a='    private JsonObject intent(';b='    private void flags('
        self.assertEqual(self.base[self.base.index(a):self.base.index(b)],self.source[self.source.index(a):self.source.index(b)])

    def test_legacy_population_branch_is_preserved_and_scale_is_explicit(self):
        start='    private void population(boolean create)throws Exception{'
        end='    @SuppressWarnings({"rawtypes","unchecked"}) private static BlockState parse'
        old=self.base[self.base.index(start):self.base.index(end)]
        end_new='    private void scaleLedgerSlice()'
        new=self.source[self.source.index(start):self.source.index(end_new)]
        new=new.replace('        if(scaledPopulation){scaledPopulation(create);return;}\n','')
        self.assertEqual(old.strip(),new.strip())
        self.assertIn('scaledPopulation=request.get("format").getAsString().equals("awft-native-habitat-life:4")',self.source)
        self.assertIn('if(scaledPopulation){cohortLimit=64;',self.source)
        self.assertIn('Actual expanded1m habitat extent required',self.source)


if __name__=='__main__':unittest.main()
