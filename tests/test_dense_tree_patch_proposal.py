from pathlib import Path
import hashlib
import unittest

from tools.artistic_dense_tree_patch_proposal import BASES,transform_controller,transform_scope,transform_bees


class DenseTreePatchProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[1]
        cls.folder=cls.root/'compat/proposals/dense-tree-patch49'

    def test_complete_native_proposals_derive_from_exact_owned_bases(self):
        names={'NativeTreeGrowthSupport':('NativeTreePatchSupport',transform_controller),
               'TreeGrowthScope':('TreeGrowthScope',transform_scope),'TreeBeeAudit':('TreeBeeAudit',transform_bees)}
        for old,(new,transform)in names.items():
            with self.subTest(old=old):
                base=self.folder/f'{old}48-base.java.txt'
                self.assertEqual(BASES[old],hashlib.sha256(base.read_bytes()).hexdigest())
                self.assertEqual(transform(base.read_text()),(self.folder/f'{new}.java').read_text())

    def test_legacy_scope_constructor_remains_strict_and_existing_logs_never_overlap(self):
        source=(self.folder/'TreeGrowthScope.java').read_text()
        self.assertIn('this(level,before,writeBounds,protectedColumns,soilY,allowNativeNest,Set.of());',source)
        self.assertIn('||original.is(BlockTags.LOGS)',source)
        self.assertIn('desired.getBlock()instanceof LeavesBlock&&desired.is(BlockTags.LEAVES)',source)
        self.assertIn('original.getBlock()instanceof LeavesBlock&&original.is(BlockTags.LEAVES)',source)
        self.assertIn('if(!desired.equals(original)||!scope.attempted.contains(position))',source)

    def test_durable_field_and_intent_then_atomic_native_growth_without_an_extra_roll(self):
        source=(self.folder/'NativeTreePatchSupport.java').read_text()
        grow=source[source.index('    private void grow()'):source.index('    public void tick(')]
        self.assertLess(grow.index('PreMutationFieldCheck.requireUnchanged'),grow.index('scope.hookWitness(root)'))
        self.assertLess(grow.index('scope.hookWitness(root)'),grow.index('rootIntent();'))
        self.assertLess(grow.index('rootIntent();'),grow.index('level.setBlock(root,sapling,3)'))
        self.assertEqual(1,grow.count('target.isBonemealSuccess('))
        self.assertEqual(1,grow.count('target.performBonemeal('))
        self.assertIn('if(stage==1&&next.getBlock()==sapling.getBlock())throw',grow)
        self.assertIn('heldRoots.contains(p)',source)
        self.assertIn('A prior dense-patch root intent remains',source)
        self.assertIn('if(clean&&terminalPublished)phase=Phase.IDLE',source)

    def test_native_failed_recovery_and_bee_checks_are_preserved(self):
        before=(self.folder/'NativeTreeGrowthSupport48-base.java.txt').read_text()
        after=(self.folder/'NativeTreePatchSupport.java').read_text()
        a='    private void recoverGrowth(';b='    private void grow()'
        self.assertEqual(before[before.index(a):before.index(b)],after[after.index(a):after.index(b)])
        base=(self.folder/'TreeBeeAudit48-base.java.txt').read_text()
        changed=(self.folder/'TreeBeeAudit.java').read_text()
        a='    /** Called by the scoped setter'
        self.assertEqual(base[base.index(a):],changed[changed.index(a):])


if __name__=='__main__':unittest.main()
