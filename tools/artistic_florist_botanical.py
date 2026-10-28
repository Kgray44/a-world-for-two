"""One measured Marigold & Tide botanical/depth pilot, never a town rollout.

New targets are literal saved AIR only. Existing interiors, windows, inventories,
walking bodies and cable reservations remain unchanged. No native actions.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from collections import deque
from pathlib import Path
from zipfile import ZipFile

from control_room.common import UserError,digest,read_json
from tools import artistic_botanical as bot
from tools.artistic_bridge_refinement import flatten
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_north_bank_east import NorthTerrain,native_payload
from tools.artistic_north_bank_west import ZIPLINE_MASK,ZIPLINE_MASK_SHA
from tools.settlement_attractions import properties
from tools.playtest import guard

MIB=1024**2
OWNER='Marigold & Tide full shop and small side garden'
BASE='staging/north-bank-west-five-final-20261028T0200Z'
BASE_PLAN=(BASE+'/florist-PROPOSAL.json','2b5058dbc498f5c63bad69e0694c9c6fbc9625a5933c4aa7e28cc8d80ebc7a8a')
BASE_MANIFEST=(BASE+'/manifest.json','7e8f392abbb71eec606cc7b2158a541d6689744cea22c125571a5214427c4254')
CHECKPOINT=('20261028T043630Z-e55a8c','4384206f639659b09b2d332d2eb058241ca6dc15298f3808745025ed85992fac')
RESERVES=(
 ('staging/west-street-stock-SNBT-fixed-20261028T0317Z/future-walk-furniture-reservation-ONLY.json','59e708726681c29ef962f632f3572369ec1db0299d58e11b454b6259b09be905'),
 ('staging/north-bank-western-connections-r2-1793159711602697500/connections.json','b658552ec91b6cd681a3e847dfe9613f51fcf59ca584642a3b184ba7c4e2956a'),
 ('staging/north-bank-west-extra-court-routes-1793161504975467000/connections.json','4cdd0d214586206c9ba6626be2e879022a0d604f91a3e89959fcfae70208372d'),
)
POTS=('regions_unexplored:potted_aster','regions_unexplored:potted_bleeding_heart',
      'regions_unexplored:potted_felicia_daisy','fishofthieves:potted_pink_plumeria',
      'fishofthieves:potted_tropical_monstera')
NEW_LOG='minecraft:stripped_cherry_log'
LEAVES={'minecraft:cherry_leaves','regions_unexplored:flowering_leaves'}
FAMILIES=(
 ('regions-unexplored-0.6.3-neoforge-21.1.jar',6641783,'744b7c37cfc7613c0c5f8507a309f61adcb117ab4ac1c572ea7b167fa7bc64d6ab0096ef7a1f0be7d33c0614cf01f76b88f25cf35936040938930c82c8f42501','net/regions_unexplored/registry/RUBlocks.class','net/minecraft/world/level/block/FlowerPotBlock'),
 ('fish_of_thieves-mc1.21.1-v21.1.3.0-neoforge.jar',1902440,'c6d65cebdb86b37c9e83c780c3e18b1de51842e14d4ac87a5636083b77fbc3f69359d1e27a5537452bc41f9243f3be3d8ce10d06eb249a0b7479d927ee738787','com/stevekung/fishofthieves/registry/FOTBlocks.class','net/minecraft/world/level/block/FlowerPotBlock'),
 ('chipped-neoforge-1.21.1-4.0.2.jar',15020578,'f3083b01267e7c674c4b42f45a317c93ee7723443cba2051fe5bc593638b533b0fe90699e2101661c934dff458eab693cce4e188533bfe977778c249563a2fa5','earth/terrarium/chipped/common/registry/ModBlocks.class','net/minecraft/world/level/block/VineBlock'),
)


def checked(home,ref):
    p=home/ref[0]
    if not p.resolve().is_relative_to(home/'staging') or p.is_symlink() or not 0<p.stat().st_size<=4*MIB or digest(p)!=ref[1]:raise UserError('Exact florist owner/reservation changed')
    return read_json(p)


def native_family_witness():
    """Pinned primary bytecode references, explicitly below native survival."""
    rows=[]
    for name,size,sha,member,reference in FAMILIES:
        p=Path('D:/A World for Two/caches/mods')/name
        if p.is_symlink() or p.stat().st_size!=size:raise UserError('Exact pinned plant-family artifact size required')
        hasher=hashlib.sha512()
        with p.open('rb') as stream:
            for block in iter(lambda:stream.read(65536),b''):hasher.update(block)
        if hasher.hexdigest()!=sha:raise UserError('Pinned plant-family artifact bytes differ')
        with ZipFile(p) as archive:
            if not 0<archive.getinfo(member).file_size<=512*1024:raise UserError('Finite native plant-family class required')
            code=archive.read(member)
        if reference.encode() not in code:raise UserError('Reviewed native plant-family reference changed')
        rows.append({'filename':name,'bytes':size,'sha512':sha,'registration_class':member,
            'class_sha256':hashlib.sha256(code).hexdigest(),'native_class_reference':reference,
            'meaning':'Actual pinned registration-class reference only; not concrete native instance/canSurvive/runtime acceptance'})
    return rows


def ground_root(garden,pos):
    """A post rests on real dry full ground, including a bounded gravel stack."""
    p=tuple(pos)
    for _ in range(8):
        value=garden.actual(p)
        if p in garden.saved_bes:raise UserError('A block entity cannot be a garden post footing')
        if bot.key(value) in bot.STURDY:
            garden.roots[p]=value;return
        if bot.key(value) not in {'minecraft:gravel','minecraft:sand','minecraft:red_sand'}:
            raise UserError('A real dry stable garden footing is required '+str((p,value)))
        garden.roots[p]=value;p=bot.plus(p,(0,-1,0))
    raise UserError('Unproven loose-ground footing beyond the finite eight-cell witness')


def flowered_ledge(g):
    """An embedded cantilever below, not across, the fancy upper glazing."""
    def action():
        for x,pot in zip((1082,1083,1084),POTS):
            g.root((x,66,-1249));g.root((x,65,-1249))
            for z in (-1250,-1251):g.put(OWNER,(x,66,z),'chipped:flowering_cherry_log',axis='z')
            g.put(OWNER,(x,67,-1251),pot)
        for x in (1082,1084):g.put(OWNER,(x,65,-1250),'mythrais:curved_corbel_dark_oak',facing='north',shape=0)
    g.atomic('Low projecting carved cherry flower ledge below the upper oriel',OWNER,action)


def attached_ivy(g,lower,face,height,flowering=False):
    normal=bot.FACES[face]
    def action():
        for y in range(height):
            p=bot.plus(lower,(0,y,0));g.root(bot.plus(p,normal,-1))
            flags={side:False for side in ('east','west','north','south','up')};flags[bot.OPPOSITE[face]]=True
            g.put(OWNER,p,'chipped:flowery_vine' if flowering else 'chipped:ivy_vine',**flags)
    g.atomic('Side-attached flowering ivy on literal solid wall '+str(lower),OWNER,action)


def berry_fitting(g,wall,face):
    normal=bot.FACES[face]
    def action():
        g.root(wall);g.root(bot.plus(wall,(0,-1,0)))
        for n in (1,2):g.put(OWNER,bot.plus(wall,normal,n),'chipped:flowering_cherry_log',axis='x' if normal[0] else 'z')
        g.put(OWNER,bot.plus(bot.plus(wall,normal),(0,-1,0)),'mythrais:small_curved_corbel_dark_oak',facing=face,shape=0)
        for n in (1,2,3):
            p=bot.plus(bot.plus(wall,normal,2),(0,-n,0))
            g.put(OWNER,p,'minecraft:cave_vines' if n==3 else 'minecraft:cave_vines_plant',**({'age':25,'berries':True} if n==3 else {'berries':n==1}))
    g.atomic('Small carved eave bracket with real underside-rooted berry pendant',OWNER,action)


def rooted_pot(g,pos,pot):
    def action():
        ground_root(g,bot.plus(pos,(0,-1,0)))
        g.put(OWNER,pos,'minecraft:chiseled_stone_bricks')
        g.put(OWNER,bot.plus(pos,(0,1,0)),pot)
    g.atomic('Contained native flowerpot on a fixed dry stone pedestal '+str(pos),OWNER,action)


def leaf_distances(states):
    """Literal face-adjacent paths to real new vanilla log blocks, max six."""
    leaves={p for p,v in states.items() if bot.key(v) in LEAVES}
    logs={p for p,v in states.items() if bot.key(v)==NEW_LOG}
    distances={p:0 for p in logs};todo=deque(logs)
    while todo:
        p=todo.popleft();distance=distances[p]+1
        if distance>6:continue
        for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            q=bot.plus(p,d)
            if q in leaves and q not in distances:distances[q]=distance;todo.append(q)
    if leaves-set(distances):raise UserError('A decorative garden garland has no actual adjacent-log leaf path')
    return {p:distances[p] for p in leaves}


def cherry_trellis(g):
    """A narrow garden screen with real posts, not a stamped tree or alley roof."""
    def action():
        for z in (-1244,-1240):
            ground_root(g,(1093,63,z))
            for y in range(64,67):g.put(OWNER,(1093,y,z),NEW_LOG,axis='y')
            g.put(OWNER,(1093,67,z),'chipped:carved_stripped_cherry_log',axis='y')
            g.put(OWNER,(1093,68,z),NEW_LOG,axis='z')
        for z in (-1243,-1242,-1241):
            g.put(OWNER,(1093,68,z),'minecraft:cherry_slab',type='bottom',waterlogged=False)
            for y in (65,66,67):
                g.put(OWNER,(1093,y,z),'chipped:vined_cherry_trapdoor',facing='west',half='bottom',open=True,powered=False,waterlogged=False)
        garland={(1093,69,z):'minecraft:cherry_leaves' for z in range(-1244,-1239)}
        garland.update({(1092,69,-1243):'regions_unexplored:flowering_leaves',(1094,69,-1241):'regions_unexplored:flowering_leaves',(1093,70,-1242):'minecraft:cherry_leaves'})
        paths=leaf_distances(g.blocks|garland)
        for p,name in garland.items():g.put(OWNER,p,name,distance=paths[p],persistent=True,waterlogged=False)
    g.atomic('Compact cherry garland trellis beside the preserved two-wide alley',OWNER,action)


def construct(g):
    flowered_ledge(g)
    attached_ivy(g,(1081,65,-1250),'north',3,True)
    attached_ivy(g,(1087,65,-1250),'north',2)
    attached_ivy(g,(1080,65,-1242),'west',3)
    attached_ivy(g,(1083,65,-1241),'south',3)
    berry_fitting(g,(1081,71,-1244),'west')
    berry_fitting(g,(1083,71,-1242),'south')
    cherry_trellis(g)
    for p,pot in (((1094,64,-1244),POTS[3]),((1094,64,-1242),POTS[4]),((1079,64,-1248),POTS[1]),((1079,64,-1241),POTS[2])):rooted_pot(g,p,pot)
    if not 60<=len(g.blocks)<=200:raise UserError('The single florist pilot must remain60..200 cells')
    return g


def prepare(home):
    home=Path(home).resolve();reserve=guard(2*MIB,8*MIB)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Exact owned private florist home required')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or (receipt.get('id'),receipt.get('sha256'))!=CHECKPOINT:raise UserError('Exact clean post-recovery e55 florist checkpoint required')
    registry=read_json(home/'dashboard/settlement/registry.json');source=checked(home,BASE_PLAN);manifest=checked(home,BASE_MANIFEST);authored=flatten(source);families=native_family_witness()
    if any(str(source[k])!=str(registry[k]) for k in ('seed','world_path')):raise UserError('Flower shop source belongs to another world')
    reserved={p for p,v in authored.items() if bot.key(v) in bot.AIR};custody=[]
    for relative,sha in (*RESERVES,(ZIPLINE_MASK,ZIPLINE_MASK_SHA)):
        reserved.update(flatten(checked(home,(relative,sha))));custody.append({'path':relative,'sha256':sha,'meaning':'Existing/future source keepout, not observed saved AIR'})
    lot=manifest['lots']['florist']
    for route in lot['routes']:
        for p in route:
            for dy in (1,2):reserved.add(bot.plus(p,(0,dy,0)))
    # Independent literal side passage, left completely open at native feet64.
    passage={(x,y,z) for x in (1091,1092) for z in range(-1245,-1238) for y in (64,65)};reserved.update(passage)
    for p,s in authored.items():
        if any(w in bot.key(s) for w in ('window','door','sign')):
            face=properties(s).get('facing')
            if face in bot.FACES:
                for n in (1,2):reserved.add(bot.plus(p,bot.FACES[face],n))
    terrain=NorthTerrain(home,receipt,registry)
    try:
        actual_owner={p:terrain.state(*p) for p in authored}
        # Exact reviewed normal default expansion of the original short block
        # ID. This cell is retained and never placed by the pilot.
        shorthand=(1087,65,-1243)
        expected_owner=dict(authored)
        if authored[shorthand]!='chipped:botanist_workbench':raise UserError('The reviewed original shorthand changed')
        expected_owner[shorthand]='chipped:botanist_workbench[facing=north,model=main]'
        if actual_owner!=expected_owner:raise UserError('Retained complete flower shop differs; inspect without replaying source')
        body={p:terrain.state(*p) for p in passage}
        if any(bot.key(v) not in bot.AIR for v in body.values()):raise UserError('The literal side alley is not already clear')
        g=construct(bot.Garden(registry,lambda p:terrain.state(*p),terrain.entities,reserved,set()))
        if any(not (1078<=x<=1094 and 64<=y<=74 and -1252<=z<=-1240) for x,y,z in g.blocks):raise UserError('Single flower shop pilot escaped its compact fixed envelope')
        material=require_material_rule(actual_owner|g.blocks,OWNER)
        require_outdoor_rule(actual_owner|g.blocks,'Complete florist shop, new garland, side screen and planted ledge')
        if set(g.blocks)&set(actual_owner):raise UserError('No original florist cell, including interior AIR, can be changed')
        native_bes=[list(p) for p in sorted(terrain.entities) if 1078<=p[0]<=1094 and -1253<=p[2]<=-1238]
        if any(sum(abs(a-b) for a,b in zip(p,q))<=1 for p in g.blocks for q in native_bes):raise UserError('A botanical target is adjacent to a retained inventory/model BE')
        saved=terrain.snapshot.sources
    finally:terrain.close()
    docs={'botanical-depth-PROPOSAL.json':native_payload(registry,g.blocks,CHECKPOINT[1],'One florist botanical-depth pilot: new AIR targets only'),
        'before-VERIFY-ONLY.json':native_payload(registry,g.previous,CHECKPOINT[1],'VERIFY ONLY: exact saved AIR before the florist pilot'),
        'supports-and-alley-VERIFY-ONLY.json':native_payload(registry,g.roots|body,CHECKPOINT[1],'VERIFY ONLY: actual stable supports and unchanged clear two-wide alley'),
        'full-shop-and-pilot-VERIFY-ONLY.json':native_payload(registry,actual_owner|g.blocks,CHECKPOINT[1],'VERIFY ONLY: whole retained actual shop and newpilot; never replay containers or original source')}
    raw={name:(json.dumps(d,separators=(',',':'),ensure_ascii=False)+'\n').encode() for name,d in docs.items()}
    report={'format':'awft-single-florist-botanical-depth-pilot:1','source_sha256':digest(Path(__file__)),'checkpoint_id':CHECKPOINT[0],'checkpoint_sha256':CHECKPOINT[1],
        'new_targets':len(g.blocks),'owner_cells_retained':len(actual_owner),'scenes':g.scenes,'material_rule':material,'retained_owner_source':{'path':BASE_PLAN[0],'sha256':BASE_PLAN[1]},
        'retained_source_default_expansion':{'position':list(shorthand),'original':'chipped:botanist_workbench','native_default':'chipped:botanist_workbench[facing=north,model=main]','placement':False},
        'preserved_saved_BE_positions':native_bes,'new_BE_NBT_or_entity_spawns':0,'pinned_native_class_family_witness':families,'source_keepouts':custody,'native_actions':0,'world_writes':0,
        'leaf_attachment':'Every garland leaf has a literal face-adjacent path of at most6 to new vanilla cherry logs; persistent garden foliage, not a fabricated default tree',
        'plant_semantics':'Contained RU/Fish-of-Thieves flowerpots; side-rooted native Chipped vines; native berry vines on actual new full timber undersides. No loose sapling/azalea or inventory copying.',
        'remaining_gates':['Exact native before/supports check','Native canSurvive and ordinary neighbor settle including actual vine attachment/leaf distance','Actual inventory custody remains separate from block-only full verification','Native floor-level, day/night shader views and a real two-wide walk','Owner artistic acceptance before propagating this pilot'],
        'cameras':[{'name':'flower-oriel','feet':[1084.5,65,-1255.5],'look_at':[1083,68,-1249]},{'name':'flower-side-garden','feet':[1091.5,65,-1247.5],'look_at':[1093,67,-1241]},{'name':'flower-lantern-pendants','feet':[1076.5,65,-1242.5],'look_at':[1080,70,-1243]}],
        'native_visual_or_survival_acceptance':False,'saved_sources':saved,'reserve_guard':reserve,'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in raw.items()}}
    raw['manifest.json']=(json.dumps(report,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    if sum(map(len,raw.values()))>8*MIB:raise UserError('Finite florist output exceeded')
    out=home/'staging'/('florist-botanical-depth-'+str(time.time_ns()));out.mkdir()
    for name,b in raw.items():(out/name).open('xb').write(b)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'new_targets':len(g.blocks),'retained_owner':len(actual_owner),'scenes':len(g.scenes),'files':report['files'],'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
