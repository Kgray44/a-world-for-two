"""One original Rose Reach approach/facade pilot; source only while KG plays.

The current-game world is never read. An immutable e55 preservation baseline is
not canonical roof acceptance and cannot authorize placing over later progress.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
from collections import Counter
from zipfile import ZipFile

from control_room.common import UserError,digest,read_json
from tools import artistic_botanical as bot
from tools.artistic_florist_botanical import CHECKPOINT,leaf_distances,native_family_witness
from tools.artistic_north_bank_east import NorthTerrain,native_payload,AIR,SOFT,NORTH_SOFT,GROUND,BRIDGE,SIGNAL
from tools.artistic_north_bank_west import ZIPLINE_MASK,ZIPLINE_MASK_SHA
from tools.artistic_bridge_refinement import flatten
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_spawn_plaza import state
from tools.settlement_attractions import properties
from tools.playtest import guard

MIB=1024**2
ROSE=('staging/north-bank-rose-reach-1793151923325885400/prototype.json','831a8e6eb1e757502328d259d0846fff14e325e8ed704dae527cd7fc90cdbc37')
ROSE_META='staging/north-bank-rose-reach-1793151923325885400/manifest.json'
OTHER52=(SIGNAL,BRIDGE,
 ('staging/north-bank-compass-bend-1793156177505399400/prototype.json','cc83762b5e3e8476dc2e26ade1d84c21bca545e937d64938cbf0f43afa393b1e'),
 ('staging/north-bank-eastern22-1793157301590833400/prototype.json','956b58ce5a68a008fb7e3e099962c3f51712af604072a77fd2f81d6b7668375c'),
 ('staging/north-bank-western-ten-1793158436435294000/prototype.json','e8c8b3c74175d49c0d512abfcdac0d7e84a7d39f31ee92e8ad352755f2f7e2ef'),
 ('staging/north-bank-west-five-final-20261028T0200Z/future-solid-AIR-route-reservation-ONLY.json','c5236daf51002d6297f72e56c3b49561f0ccb2b91de301b2c5a02d9d443be17a'),
)
PAVED={'minecraft:stone_bricks','minecraft:cobblestone','minecraft:andesite','minecraft:polished_andesite','minecraft:chiseled_stone_bricks','minecraft:mossy_cobblestone','chipped:small_stone_bricks'}
COMPASS='The Gilded Compass exterior'
STREET='Rose Reach planted approach'
ARCH='A single shallow garden arbor'
BED={(1296,65,-1250):'minecraft:blue_bed[facing=north,occupied=false,part=head]',(1296,65,-1249):'minecraft:blue_bed[facing=north,occupied=false,part=foot]'}
MAIN_CENTRES=[(1285,z) for z in range(-1246,-1243)]+[(x,-1244) for x in range(1286,1291)]+[(1290,-1243),(1291,-1243),(1291,-1242)]
SIDE_CENTRES=[(1291,z) for z in range(-1256,-1246)]+[(1290,-1247),(1290,-1246),(1290,-1245),(1290,-1244)]


def columns(centres):return {(x+dx,z+dz) for x,z in centres for dx,dz in ((0,0),(1,0),(0,1),(1,1))}


def basket_provenance():
    row=next(r for r in read_json(Path('catalog/lock.json'))['mods'] if r['slug']=='supplementaries')
    if row['filename']!='supplementaries-1.21.1-4.0.2-neoforge.jar':raise UserError('Reviewed native manual basket pin changed')
    path=Path('D:/A World for Two/caches/mods')/row['filename'];h=hashlib.sha512()
    if path.stat().st_size!=row['size'] or row['size']>16*MIB:raise UserError('Exact bounded manual basket artifact required')
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(65536),b''):h.update(chunk)
    if h.hexdigest()!=row['hashes']['sha512']:raise UserError('Native manual basket bytes differ')
    classes={}
    with ZipFile(path) as archive:
        for member in ('net/mehvahdjukaar/supplementaries/common/block/blocks/LunchBoxBlock.class','net/mehvahdjukaar/supplementaries/common/block/tiles/LunchBoxBlockTile.class'):
            if archive.getinfo(member).file_size>128*1024:raise UserError('Native basket class exceeds finite read')
            classes[member]=hashlib.sha256(archive.read(member)).hexdigest()
    return {'filename':row['filename'],'sha512':h.hexdigest(),'class_sha256':classes,
        'reviewed_api':'LunchBoxBlock extends WaterBlock; LunchBoxBlockTile extends OpenableContainerBlockTile; native manual menu/open lifecycle. Exact registered default properties, no enabled/collection-disable NBT or Items stock invented.',
        'native_placement_and_interaction_proof':False}


class RoseGarden(bot.Garden):
    def root(self,pos,*,soil=False):
        # The retained approach has a vanilla packed-mud plinth. It is a full
        # solid native block, unlike mud's lower collision or an unknown model.
        pos=bot.point(pos);actual=self.actual(pos)
        if not soil and actual=='minecraft:packed_mud' and pos not in self.saved_bes:
            self.roots[pos]=actual;return actual
        return super().root(pos,soil=soil)

    def put(self,owner,pos,name,**props):
        # Unlike the separately frozen florist AIR-only pilot, this new recipe
        # explicitly replaces ordinary grass in its enumerated garden pockets.
        # The true previous state is recorded; no synthetic AIR is substituted.
        pos=bot.point(pos);actual=self.actual(pos)
        if not (1284<=pos[0]<=1294 and 64<=pos[1]<=74 and -1257<=pos[2]<=-1237):raise UserError('Single Rose Reach pilot escaped its fixed envelope')
        if pos in self.saved_bes or pos in self.reserved_body or pos in self.blocks or bot.key(actual) not in AIR|SOFT|NORTH_SOFT or 'waterlogged=true' in actual:
            raise UserError('Preserve actual object, route, BE or reserved plant view '+str((pos,actual)))
        self.previous[pos]=actual;self.blocks[pos]=state(self.registry,name,**props);self.owners[pos]=owner
        if len(self.blocks)>200:raise UserError('Single Rose Reach pilot exceeds200 targets')

    def complete_double_cover(self):
        for p,old in list(self.previous.items()):
            if old=='minecraft:tall_grass[half=lower]':
                q=bot.plus(p,(0,1,0))
                if q not in self.blocks and self.actual(q)=='minecraft:tall_grass[half=upper]':self.put(self.owners[p],q,'minecraft:air')


def paving(x,z):
    return 'minecraft:chiseled_stone_bricks' if x%8==0 and z%8==0 else 'minecraft:polished_andesite' if x%8==0 else 'minecraft:mossy_cobblestone' if z%8==0 else 'minecraft:cobblestone'


def pave_saved_routes(terrain,reserved,authored):
    """Only enumerated natural soil becomes paving; every old tile is retained."""
    delta={};before={};unchanged={};paths=[]
    for name,centres in (('Old stair return into the new lane',MAIN_CENTRES),('Two-wide chartmaker alley around retained fern stand',SIDE_CENTRES)):
        for x,z in sorted(columns(centres)):
            q=x,63,z;floor=terrain.state(*q)
            if q in terrain.entities or floor is None:raise UserError('Unknown/BE route support')
            if bot.key(floor) in GROUND:
                if q in authored:raise UserError('An authored soil/foundation cannot be relabeled as spare lawn')
                before[q]=floor;delta[q]=paving(x,z)
            elif bot.key(floor) in PAVED:unchanged[q]=floor
            else:raise UserError('Preserve an actual non-natural route support '+str((q,floor)))
            for y in (64,65):
                p=x,y,z;actual=terrain.state(*p)
                if actual is None or p in terrain.entities or bot.key(actual) not in AIR|SOFT|NORTH_SOFT or 'waterlogged=true' in actual:raise UserError('Literal two-wide route has an existing obstruction '+str((p,actual)))
                if bot.key(actual) in AIR:unchanged[p]=actual
                else:
                    if p in authored or p in reserved:raise UserError('Preserve an authored planted/body cell')
                    before[p]=actual;delta[p]='minecraft:air'
        paths.append({'name':name,'centres_xz':[list(p) for p in centres],'floor_y':63,'width':2,'body_y':[64,65],'native_walking':'PENDING after fresh actual preimages; do not move the current player'})
    return delta,before,unchanged,paths


def ivy(g,owner,lower,face,height,flowering=False):
    def action():
        normal=bot.FACES[face]
        for n in range(height):
            p=bot.plus(lower,(0,n,0));g.root(bot.plus(p,normal,-1))
            flags={s:False for s in ('north','south','east','west','up')};flags[bot.OPPOSITE[face]]=True
            g.put(owner,p,'chipped:flowery_vine' if flowering else 'chipped:ivy_vine',**flags)
    g.atomic('Side-rooted planted wall accent '+str(lower),owner,action)


def compass_niche(g):
    def action():
        for z,pot in ((-1253,'regions_unexplored:potted_aster'),(-1252,'fishofthieves:potted_tropical_monstera')):
            for y in (64,65):g.root((1294,y,z))
            g.put(COMPASS,(1293,64,z),'mythrais:small_curved_corbel_dark_oak',facing='west',shape=0)
            g.put(COMPASS,(1293,65,z),'minecraft:dark_oak_slab',type='top',waterlogged=False)
            g.put(COMPASS,(1293,66,z),pot)
            g.put(COMPASS,(1293,67,z),'chipped:vined_dark_oak_trapdoor',facing='west',half='bottom',open=True,powered=False,waterlogged=False)
            g.put(COMPASS,(1293,68,z),'minecraft:dark_oak_slab',type='top',waterlogged=False)
    g.atomic('Two shallow carved garden niches between actual casement windows',COMPASS,action)
    ivy(g,COMPASS,(1293,69,-1253),'west',3,True)
    def pendant():
        wall=(1294,71,-1252);g.root(wall);g.root((1294,70,-1252))
        for x in (1293,1292):g.put(COMPASS,(x,71,-1252),'chipped:flowering_dark_oak_log',axis='x')
        g.put(COMPASS,(1293,70,-1252),'mythrais:small_curved_corbel_dark_oak',facing='west',shape=0)
        for y in (70,69,68):g.put(COMPASS,(1292,y,-1252),'minecraft:cave_vines' if y==68 else 'minecraft:cave_vines_plant',**({'age':25,'berries':True} if y==68 else {'berries':y==70}))
    g.atomic('A small carved berry-lit corner bracket beside the chart windows',COMPASS,pendant)


def arbor(g):
    def action():
        for x in (1290,1293):
            g.root((x,63,-1248))
            for y in (64,65,66):g.put(ARCH,(x,y,-1248),'minecraft:stripped_cherry_log',axis='y')
            g.put(ARCH,(x,67,-1248),'chipped:carved_stripped_cherry_log',axis='y')
        for x in range(1289,1295):g.put(ARCH,(x,68,-1248),'minecraft:stripped_cherry_log',axis='x')
        # The eastern tip is a one-block timber cantilever: its lower knee
        # would occupy the actual cropped-corner casement view. Keep it open.
        g.put(ARCH,(1289,67,-1248),'mythrais:small_curved_corbel_dark_oak',facing='west',shape=0)
        leaves={(x,69,-1248):'minecraft:cherry_leaves' for x in range(1289,1295)}
        leaves[1291,70,-1248]='regions_unexplored:flowering_leaves'
        for p,distance in leaf_distances(g.blocks|leaves).items():
            if p in leaves:g.put(ARCH,p,leaves[p],distance=distance,persistent=True,waterlogged=False)
        for x in (1291,1292):g.put(ARCH,(x,67,-1248),'minecraft:cave_vines',age=25,berries=True)
    g.atomic('One shallow cherry arbor with open sky beyond, not a covered street',ARCH,action)


def planted_edges(g):
    ivy(g,STREET,(1284,64,-1247),'east',3)
    ivy(g,STREET,(1284,64,-1244),'east',3,True)
    def flowers():
        for z,name in ((-1246,'regions_unexplored:aster'),(-1245,'regions_unexplored:bleeding_heart'),(-1243,'regions_unexplored:felicia_daisy'),(-1238,'regions_unexplored:pink_lupine')):
            g.root((1284,63,z),soil=True);g.put(STREET,(1284,64,z),name)
    g.atomic('An uneven rooted flower edge beside, not inside, the two-wide return',STREET,flowers)
    for p,pot in (((1289,64,-1250),'regions_unexplored:potted_bleeding_heart'),((1289,64,-1255),'fishofthieves:potted_pink_plumeria'),((1286,64,-1237),'regions_unexplored:potted_felicia_daisy')):
        def stand(p=p,pot=pot):
            g.root(bot.plus(p,(0,-1,0)))
            g.put(STREET,p,'minecraft:chiseled_stone_bricks');g.put(STREET,bot.plus(p,(0,1,0)),pot)
        g.atomic('A contained corner pot on an actual stable dry pedestal '+str(p),STREET,stand)
    def market():
        for z in (-1252,-1253):g.root((1289,63,z))
        g.put(STREET,(1289,64,-1252),'chipped:flowering_cherry_log',axis='y')
        g.put(STREET,(1289,65,-1252),'handcrafted:berry_jam_jar',facing='south',jars=2,waterlogged=False)
        g.put(STREET,(1289,64,-1253),'supplementaries:lunch_basket',dyed=False,facing='west',hanging=False,open=False,waterlogged=False)
    g.atomic('A tiny empty manual lunch basket and jar display; no collector state forged',STREET,market)


def audited_owner(actual,source):
    """Preservation-only identity check, never normal roof-state acceptance."""
    differences=[]
    for p,old in source.items():
        now=actual[p]
        if now==old:continue
        if p in BED:
            if old!='minecraft:air' or now!=BED[p]:raise UserError('Authorized bed baseline differs')
            differences.append({'position':list(p),'kind':'Previously authorized real HOME bed'});continue
        if bot.key(now)!=bot.key(old):raise UserError('Retained Rose building identity differs '+str(p))
        old_props=properties(old);new_props=properties(now);changed={k for k,v in old_props.items() if new_props.get(k)!=v}
        allowed={'shape'} if bot.key(old) in ('mcwroofs:dark_oak_roof','mcwroofs:red_terracotta_roof') else {'pillar_connection'} if bot.key(old)=='dawnoftimebuilder:spruce_support_slab' else set()
        if changed-allowed:raise UserError('Unreviewed retained Rose orientation/state change '+str((p,changed)))
        differences.append({'position':list(p),'kind':'Observed prior native defaults/derived connections retained unchanged; not a canonical acceptance','properties':sorted(changed)})
    return differences


def prepare(home):
    home=Path(home).resolve();reserve=guard(2*MIB,8*MIB)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Owned Rose pilot home required')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or (receipt.get('id'),receipt.get('sha256'))!=CHECKPOINT:raise UserError('Exact clean e55 source required; no live/crash-world fallback')
    registry=read_json(home/'dashboard/settlement/registry.json');source={};custody=[]
    for relative,sha in (ROSE,*OTHER52,(ZIPLINE_MASK,ZIPLINE_MASK_SHA)):
        path=home/relative
        if not 0<path.stat().st_size<=4*MIB or digest(path)!=sha:raise UserError('Exact retained52/source keepout changed')
        d=read_json(path)
        if any(str(d[k])!=str(registry[k]) for k in ('seed','world_path')):raise UserError('Source belongs to another world')
        cells=flatten(d)
        if (relative,sha)==ROSE:rose=cells
        source.update({p:v for p,v in cells.items() if 1280<=p[0]<=1305 and -1259<=p[2]<=-1236 and 62<=p[1]<=84})
        custody.append({'path':relative,'sha256':sha,'meaning':'All actual/future authored targets remain protected; no placement claim inferred here'})
    lots=read_json(home/ROSE_META)['buildings'];main=set().union(*(set(map(tuple,r['main_footprint'])) for r in lots))
    masks=flatten(read_json(home/ZIPLINE_MASK));reserved=set(masks)
    for p,s in rose.items():
        if 'window' in bot.key(s) or 'door' in bot.key(s) or 'sign' in bot.key(s):
            for normal in bot.FACES.values():
                if (p[0]+normal[0],p[2]+normal[2]) not in main:
                    for n in (1,2):reserved.add(bot.plus(p,normal,n))
    terrain=NorthTerrain(home,receipt,registry)
    try:
        actual_rose={p:terrain.state(*p) for p in rose};retention_notes=audited_owner(actual_rose,rose)
        floor_delta,floor_before,walk,paths=pave_saved_routes(terrain,reserved,source)
        reserved.update(p for p in walk if p[1] in (64,65));reserved.update(p for p in floor_delta if p[1] in (64,65))
        g=RoseGarden(registry,lambda p:terrain.state(*p),terrain.entities,reserved,set())
        compass_niche(g);arbor(g);planted_edges(g);g.complete_double_cover()
        clearance=[]
        for p,v in g.blocks.items():
            if p in source:
                if bot.key(source[p]) not in AIR or (p[0],p[2]) in main:raise UserError('Preserve every actual shop/interior/model cell')
                # Exact exterior construction-clearance AIR is explicitly
                # authorized for this new attached garden layer, not interiors.
                column=terrain.column(p[0],p[2])
                if p not in rose and column['kind']!='dry':raise UserError('Non-Rose authored clearance has no literal dry exterior proof')
                clearance.append(list(p))
        delta=floor_delta|g.blocks;before=floor_before|g.previous
        if set(floor_delta)&set(g.blocks):raise UserError('A planted scene collides with the exact paved route')
        if not 90<=len(delta)<=200:raise UserError('Single Rose pilot must remain90..200 targets')
        require_material_rule({p:v for p,v in actual_rose.items() if 1293<=p[0]<=1303 and -1258<=p[2]<=-1246}|{p:v for p,v in g.blocks.items() if g.owners[p]==COMPASS},'Whole Gilded Compass with its shallow botanical niches')
        require_material_rule({p:v for p,v in g.blocks.items() if g.owners[p]==ARCH},'Complete small arbor including garland and pendants')
        current_context={p:terrain.state(*p) for p in source}
        if any(v is None for v in current_context.values()):raise UserError('Preserved local context is not FULL')
        require_outdoor_rule(current_context|delta,'Whole local accepted approach plus new paving and garden')
        if set(delta)&terrain.entities:raise UserError('Preserve existing native block entities')
        saved=terrain.snapshot.sources;native_bes=[list(p) for p in sorted(terrain.entities) if 1280<=p[0]<=1305 and -1259<=p[2]<=-1236]
    finally:terrain.close()
    docs={'pilot-PROPOSAL.json':native_payload(registry,delta,CHECKPOINT[1],'One Rose Reach approach and shallow botanical facade pilot'),
        'before-VERIFY-ONLY.json':native_payload(registry,before,CHECKPOINT[1],'VERIFY ONLY: exact e55 natural/AIR pilot preimages; fresh current-user protection mandatory'),
        'roots-and-walk-VERIFY-ONLY.json':native_payload(registry,g.roots|walk,CHECKPOINT[1],'VERIFY ONLY: unchanged supports and literal2wide walking bodies'),
        'pilot-after-VERIFY-ONLY.json':native_payload(registry,delta,CHECKPOINT[1],'VERIFY ONLY: new pilot states after normal native joining and survival'),
        'retained-context-BEFORE-AND-AFTER-VERIFY-ONLY.json':native_payload(registry,current_context|actual_rose,CHECKPOINT[1],'OBSERVED PRESERVATION ONLY: retained e55 states, not canonical roof/whole-town acceptance; never place')}
    raw={n:(json.dumps(d,separators=(',',':'),ensure_ascii=False)+'\n').encode() for n,d in docs.items()}
    report={'format':'awft-single-rose-reach-botanical-pilot:1','checkpoint_id':CHECKPOINT[0],'checkpoint_sha256':CHECKPOINT[1],'source_sha256':digest(Path(__file__)),
        'new_targets':len(delta),'new_paving_and_ordinary_cover_targets':len(floor_delta),'new_botanical_3D_targets':len(g.blocks),'scenes':g.scenes,'walking_paths':paths,
        'source_custody':custody,'observed_retention_notes':retention_notes,'reviewed_exterior_source_AIR_targets':clearance,
        'preserved_native_BE_positions':native_bes,'new_native_basket':'One empty manual Supplementaries lunch basket; no enabled/collection-disable key or Items stock invented','basket_class_provenance':basket_provenance(),
        'new_NBT_or_entity_instructions':0,'no_native_actions':True,'world_writes':0,'native_visual_or_walking_acceptance':False,
        'limits':['KG is playing; no current world is read or modified','Every e55 preimage is historical; later human changes MUST refuse native admission, never be overwritten','Observed context/default/connection states are a preservation snapshot, not acceptance of old canonical roof expectations','Only one prototype; no whole72-house or whole-bank acceptance','Old Signal view at1271 is distinct from new Rose Reach'],
        'cameras':[{'name':'real-new-Rose-lane','feet':[1292.5,64,-1241.5],'look_at':[1311,71,-1242]},{'name':'Rose-entry-and-arbor','feet':[1287.5,64,-1242.5],'look_at':[1292,68,-1249]},{'name':'Gilded-casement-niches','feet':[1291.5,64,-1255.5],'look_at':[1294,68,-1252]}],
        'remaining_gates':['Fresh native preimage/unchanged-current-user checks after KG finishes','Normal native survival/join and actual inventory/BE preservation','Real walk and floor-level day/night shader composition','Owner acceptance before propagation'],
        'pinned_plant_registration_class_refs':native_family_witness(),'saved_sources':saved,'reserve_guard':reserve,'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in raw.items()}}
    raw['manifest.json']=(json.dumps(report,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    if sum(map(len,raw.values()))>8*MIB:raise UserError('Finite Rose source output exceeded')
    out=home/'staging'/('rose-reach-botanical-pilot-'+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'new_targets':len(delta),'scenes':len(g.scenes),'files':report['files'],'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
