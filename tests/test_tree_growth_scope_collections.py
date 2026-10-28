import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TreeGrowthScopeCollectionContract(unittest.TestCase):
    def test_constructor_uses_both_defensive_snapshots_before_arming(self):
        source = (ROOT / 'compat/control-bridge/src/worldfortwo/bridge/TreeGrowthScope.java').read_text(encoding='utf-8')
        constructor = source.split('public TreeGrowthScope(', 1)[1].split('public static long column', 1)[0]
        self.assertIn('this.before=snapshotMap(before)', constructor)
        self.assertIn('this.protectedColumns=snapshotSet(protectedColumns)', constructor)
        self.assertNotIn('copyOf(', source)
        self.assertLess(constructor.index('snapshotSet('), constructor.index('ACTIVE.set(this)'))

    def test_native_authority_and_latched_refusal_gates_are_retained(self):
        source = (ROOT / 'compat/control-bridge/src/worldfortwo/bridge/TreeGrowthScope.java').read_text(encoding='utf-8')
        for gate in ('!level.getServer().isSameThread()', '!scope.before.containsKey(position)',
                     'scope.protectedColumns.contains(column(position.getX(),position.getZ()))',
                     'scope.violation!=null&&!scope.rollback', 'TreeBeeAudit.desired(',
                     'scope.attempted.size()>65536||scope.writes>262144', 'if(ACTIVE.get()!=this)',
                     'armed=false;ACTIVE.remove();closed=true;'):
            self.assertIn(gate, source)


if __name__ == '__main__':
    unittest.main()
