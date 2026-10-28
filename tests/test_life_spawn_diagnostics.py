from pathlib import Path
import hashlib
import unittest

from control_room.common import UserError
from tools.artistic_life_spawn_diagnostics import BASE_SHA,OLD,NEW,METHOD,transform


class LifeSpawnDiagnosticTests(unittest.TestCase):
    def test_same_three_single_normal_calls_in_original_order(self):
        calls=('mob.checkSpawnObstruction(level)',
               'SpawnPlacements.checkSpawnRules(row.type,level,MobSpawnType.STRUCTURE,mob.blockPosition(),level.random)',
               'EventHooks.checkSpawnPosition(mob,level,MobSpawnType.STRUCTURE)')
        for call in calls:
            self.assertEqual(1,OLD.count(call));self.assertEqual(1,NEW.count(call))
        self.assertEqual(sorted(NEW.index(c)for c in calls),[NEW.index(c)for c in calls])
        self.assertEqual(3,NEW.count('throw spawnRefusal'))

    def test_failure_only_context_has_no_random_or_world_setter(self):
        for forbidden in ('level.random','nextInt(','nextFloat(','checkSpawnRules(',
                          'checkSpawnPosition(','checkSpawnObstruction(','.setBlock(','.setDayTime(',
                          '.addFreshEntity(','.setNoAi(','.setUUID('):
            self.assertNotIn(forbidden,METHOD)
        for fact in ('rejected_step','sky_light','block_light','day_time','biome','below_in_native_firefly_spawn_tag'):
            self.assertIn('"'+fact+'"',METHOD)

    def test_unknown_or_doubled_preview_is_not_rewritten(self):
        for text in ('different',OLD,OLD+'\n'+OLD+'\n    private Mob preview(Resident row)throws Exception{'):
            with self.assertRaises(UserError):transform(text)

    def test_generated_proposal_retains_all_other_controller_logic(self):
        root=Path(__file__).resolve().parents[1]
        proposed=(root/'compat/proposals/life-spawn-diagnostics-r1/NativeHabitatLifeSupport.java').read_text()
        restored=proposed.replace(METHOD,'').replace(NEW,OLD)
        self.assertEqual(BASE_SHA,hashlib.sha256(restored.encode()).hexdigest())
        self.assertEqual(transform(restored),proposed)


if __name__=='__main__':unittest.main()
