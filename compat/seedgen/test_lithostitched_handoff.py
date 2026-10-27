"""Pure source-patch contracts; no game, network, account or world access."""
import ast
import unittest
from compat.seedgen.prepare_lithostitched_handoff import builder_patch, callback_patch, contents, replace_once
from control_room.common import UserError


class HandoffPatchTests(unittest.TestCase):
    def test_callback_preserves_capture_and_orders_all_three_native_phases(self):
        before='import worldfortwo.bridge.HybridAquaticSeedgenCompat;\n// CAPTURE_FAILHARD / ordinal0 / require1\n        if(withMods)HybridAquaticSeedgenCompat.apply(worldgen,resources,stems);\n'
        after=callback_patch(before)
        sequence=['currentAttemptStems(stems)','beforeHybrid(worldgen,currentStems,wholeSet,opened,resources)',
                  'HybridAquaticSeedgenCompat.apply(worldgen,resources,currentStems)','afterHybrid(worldgen)']
        self.assertEqual(sorted(after.index(part) for part in sequence),[after.index(part) for part in sequence])
        self.assertIn('// CAPTURE_FAILHARD / ordinal0 / require1',after)
        self.assertEqual(after.count('if(withMods)'),1)

    def test_missing_or_duplicated_active_context_refuses(self):
        for text in ('not the original callback','same\nsame'):
            with self.assertRaises(UserError):replace_once(text,'same','new')

    def test_actual_builder_patch_keeps_version_and_produces_valid_compile_recipe(self):
        before=contents('tools/build_bridge.py');after=builder_patch(before)
        def version(text):
            return next(node.value.value for node in ast.parse(text).body if isinstance(node,ast.Assign)
                        and any(isinstance(t,ast.Name) and t.id=='BRIDGE_VERSION' for t in node.targets))
        self.assertEqual(version(before),version(after))
        self.assertIn('mixinextras-neoforge-0.5.5.jar',after)
        self.assertIn('jars.insert(0,client_api)',after)
        self.assertEqual(after.count('BRIDGE_VERSION ='),1)


if __name__=='__main__':unittest.main()
