"""Freeze a diagnostic-only v3 LIFE proposal; never edit the active controller."""
from pathlib import Path
import difflib
import hashlib
import json

from control_room.common import UserError, digest, utcnow
from tools.playtest import guard

BASE_SHA='b90b7b1f92ac170a8c5ea6383970fc72ff56ca51347c590ed819bfd6f69551f9'
OLD='''        if(!mob.checkSpawnObstruction(level)||!SpawnPlacements.checkSpawnRules(row.type,level,MobSpawnType.STRUCTURE,mob.blockPosition(),level.random)
            ||!EventHooks.checkSpawnPosition(mob,level,MobSpawnType.STRUCTURE))throw new IllegalStateException("Ordinary native species spawn/position hooks refused "+row.uuid);'''
NEW='''        if(!mob.checkSpawnObstruction(level))throw spawnRefusal(row,mob,"mob.checkSpawnObstruction");
        if(!SpawnPlacements.checkSpawnRules(row.type,level,MobSpawnType.STRUCTURE,mob.blockPosition(),level.random))throw spawnRefusal(row,mob,"SpawnPlacements.checkSpawnRules");
        if(!EventHooks.checkSpawnPosition(mob,level,MobSpawnType.STRUCTURE))throw spawnRefusal(row,mob,"EventHooks.checkSpawnPosition");'''
METHOD='''    /** Failure-only observations; do not rerun a predicate or consume random. */
    private IllegalStateException spawnRefusal(Resident row,Mob mob,String step){
        Map<String,Object> facts=new LinkedHashMap<>();
        facts.put("uuid",row.uuid.toString());facts.put("entity",row.id);facts.put("rejected_step",step);
        facts.put("spawn_type","STRUCTURE");facts.put("predicates_reexecuted_for_diagnostics",0);
        try{
            BlockPos p=mob.blockPosition();BlockState below=level.getBlockState(p.below());
            facts.put("block_position",List.of(p.getX(),p.getY(),p.getZ()));facts.put("below_state",below.toString());
            facts.put("sky_light",level.getBrightness(net.minecraft.world.level.LightLayer.SKY,p));
            facts.put("block_light",level.getBrightness(net.minecraft.world.level.LightLayer.BLOCK,p));
            facts.put("raw_brightness_zero_sky_darken",level.getRawBrightness(p,0));
            facts.put("max_local_raw_brightness",level.getMaxLocalRawBrightness(p));
            facts.put("sky_darken",level.getSkyDarken());facts.put("day_time",level.getDayTime());
            facts.put("is_day",level.isDay());facts.put("is_thundering",level.isThundering());
            facts.put("can_see_sky",level.canSeeSky(p));
            facts.put("biome",level.getBiome(p).unwrapKey().map(key->key.location().toString()).orElse("unregistered"));
            if(row.id.equals("naturalist:firefly"))facts.put("below_in_native_firefly_spawn_tag",below.is(net.minecraft.tags.TagKey.<Block>create(net.minecraft.core.registries.Registries.BLOCK,ResourceLocation.parse("naturalist:fireflies_spawnable_on"))));
        }catch(RuntimeException diagnosticError){facts.put("context_read_error",diagnosticError.toString());}
        report.put("spawn_hook_failure",facts);
        return new IllegalStateException("Ordinary native species spawn/position hook refused "+row.uuid+" at "+step);
    }
'''


def transform(text):
    if text.count(OLD)!=1 or text.count('    private Mob preview(Resident row)throws Exception{')!=1:
        raise UserError('Exact unchanged48 preview method required')
    return text.replace(OLD,NEW).replace('    private Mob preview(Resident row)throws Exception{',METHOD+'    private Mob preview(Resident row)throws Exception{')


def prepare():
    root=Path(__file__).resolve().parents[1]
    source=root/'compat/control-bridge/src/worldfortwo/bridge/NativeHabitatLifeSupport.java'
    if digest(source)!=BASE_SHA:raise UserError('Actual frozen48 source differs; no automatic rebase')
    output=root/'compat/proposals/life-spawn-diagnostics-r1'
    if output.exists():raise UserError('Preserve the immutable diagnostic proposal')
    reserve=guard(2*1024**2,0);old=source.read_text();new=transform(old)
    patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='native48/NativeHabitatLifeSupport.java',tofile='diagnostic-only/NativeHabitatLifeSupport.java'))
    docs={'NativeHabitatLifeSupport.java':new,'NativeHabitatLifeSupport.patch':patch,
        'README.md':'# Native LIFE spawn diagnostics\n\nThis is an isolated diagnostic-only proposal based on the exact candidate48 source. It is not installed or wired. The same three normal calls execute once each in the same left-to-right short-circuit order. No spawn predicate is rerun, no random value is sampled for diagnostics, and no darkness, block tag, event, collision, ownership or species requirement is bypassed. Failure records identify the actual rejected stage and read the live light/time/biome/underfoot context without changing it. A context-read failure is retained separately and never replaces the original refusal.\n\nThe original eight-member native48 refusal cannot retrospectively be assigned to one branch. Firefly darkness is a source-backed explanation, not a captured live-cause proof. New input/native class pins and actual runtime review are mandatory before this diagnostic source can be used.\n'}
    output.mkdir()
    for name,value in docs.items():(output/name).write_text(value,encoding='utf-8',newline='\n')
    receipt={'format':'awft-life-spawn-diagnostic-proposal:1','created':utcnow(),'base_sha256':BASE_SHA,
        'generator_sha256':digest(Path(__file__)),'native_actions':0,'installed':False,'API_compile_pending':True,
        'reserve_guard':reserve,'files':{name:{'bytes':(output/name).stat().st_size,'sha256':digest(output/name)}for name in docs}}
    (output/'source-freeze.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return {'output':str(output),'proposal_sha256':digest(output/'NativeHabitatLifeSupport.java'),'freeze_sha256':digest(output/'source-freeze.json')}


if __name__=='__main__':print(json.dumps(prepare(),indent=2))
