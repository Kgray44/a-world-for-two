"""One original hooked pirate florist and attached home: source-only first view.

Not another W3 house, not an array, and not a current-world placement request.
The unused headland must pass complete saved dry/body/support/BE checks; native
admission and actual images follow the held W3 photo-refinement gate separately.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib,json,time
import zipfile
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_west_r2_frontage import Frontage,rect,edge,canonical_joins,key
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_north_bank_east import NorthTerrain,GROUND,SOFT,NORTH_SOFT,AIR as VOIDS
from tools.artistic_bridge_refinement import flatten
from tools.artistic_zipline_catenary import reader_budget
from tools.artistic_west_r2_study import ZIP,REJECTED
from tools.playtest import guard

MIB=1024**2
NAME='Salt & Petal'
ORIGIN=(1056,64,-1305)
HALL=('staging/artistic-captains-rest-1793170982583234800/future-solid-AIR-route-reservation-ONLY.json','b4716f849de37fa9b887b5531ff93d53ce3300814f885cc93da11c007a95da54')
W3=('staging/west-r2-three-frontage-preview-1793168582590227200/three-frontages-PROPOSAL.json','336363fd0adeb0043117ce4e3ed68b32d3e7c2305d895daa68a9a027124ff5c9')
FOREST=('staging/forest47-frozen-custody-20261028T0643Z/future-native-fields-RESERVATION-ONLY.json','8f8aa4cdf7c45618761c6a524858e0f8419e9af6bf4352c26c39c61eca538376')
FOT_JAR=('fish_of_thieves-mc1.21.1-v21.1.3.0-neoforge.jar','d70f9c27b7eba24a58a04824faa0e64ac7c49eabf916c3bc2ebeab2d40dc85a8')
FOT_POTTED_REGISTRAR={'class':'com/stevekung/fishofthieves/registry/FOTBlocks.class','sha256':'76d7f004caba2697d5f359ca031ad700b0e526ea15b13dd789cfda754a944384',
    'observed_native_constructor_family':'net/minecraft/world/level/block/FlowerPotBlock','scope':'Pinned registration-class byte witness; actual native plant rendering/survival still pending'}
POTS=('fishofthieves:potted_white_plumeria','fishofthieves:potted_pink_plumeria','fishofthieves:potted_light_blue_plumeria',
      'fishofthieves:potted_tropical_monstera','fishofthieves:potted_tropical_red_fern','minecraft:potted_fern',
      'minecraft:potted_flowering_azalea_bush','minecraft:potted_blue_orchid','minecraft:potted_allium','minecraft:potted_oxeye_daisy')


def construct(registry):
    p=Frontage(registry,ORIGIN);p.owner=NAME
    main=(rect(0,0,11,9)-{(0,0),(0,1),(1,0),(11,0),(11,1),(0,9)})|rect(7,10,11,11)|rect(12,1,12,6)
    upper=rect(1,1,6,7)|rect(1,8,4,8)
    p.main[NAME]=main;p.levels[NAME]=[main,upper]
    for x,z in main:
        for y in range(1,14):p.put(x,y,z,'minecraft:air')
    p.floor(main,0);p.walls(main,0,'minecraft:gray_terracotta')
    p.floor(upper,4);p.walls(upper,4,'minecraft:green_terracotta')
    # The home rises at the west; the eastern potting room drops into a real
    # lean-to, then turns into a shallow hipped work porch at the hooked end.
    p.roof((0,0,7,9),8,(0,1,2,3,3,2,1,0),family='dark_oak')
    for x,h in ((7,8),(8,8),(9,7),(10,6),(11,5),(12,5),(13,4)):
        for z in range(0,11):p.put(x,h,z,'mcwroofs:spruce_lower_roof',facing='west',half='bottom',shape='straight')
    p.roof((6,9,12,12),4,(0,1,2,3,2,1,0),family='dark_oak',hip_south=True,annex=True)
    # The hooked porch's actual hip is solid matching dark-oak shingle steps;
    # this is a different three-dimensional end construction, never a colored
    # periodic roof stripe. The long sloping side remains the native lower roof.
    for x,h in ((6,0),(7,1),(8,2),(9,3),(10,2),(11,1),(12,0)):
        for z in range(9,13):
            clipped=12-z+1
            if clipped<h:p.stair(x,4+clipped,z,'north')
    # Four-wide three-high display is genuinely proud of the old opaque line;
    # full-height cheeks turn the glass back, making an occupied flower bay.
    for z in range(2,6):
        for y in (1,2,3):p.put(11,y,z,'minecraft:air')
    for z in range(1,7):p.beam(12,4,z,'z',wood='dark_oak',role='real continuous deep-display lintel')
    p.window(12,1,2,'east',width=4,height=3,hood='beam')
    for z in (1,6):
        for y in (1,2,3):p.put(12,y,z,'minecraft:stripped_dark_oak_log',axis='y')
        p.put(13,3,z,'mythrais:curved_corbel_dark_oak',facing='east',shape=0)
    # Slim greenhouse cheeks are different actual glass frames, not a solid
    # rectangular applique. Their window planes remain native NORTH/EAST.
    for y in (1,2,3):
        p.put(11,y,1,'mcwwindows:spruce_plank_window',facing='north',part='base')
        p.put(11,y,6,'mcwwindows:spruce_plank_window',facing='north',part='base')
    p.window(2,5,8,'south',width=2,height=2,hood='beam')
    p.window(0,1,5,'west',width=2,height=2,hood='beam')
    p.window(1,5,3,'west',width=2,height=2,hood='slant')
    p.door(9,11,'south')
    p.sign(10,3,11,'south',[NAME,'Flowers • Herbs • Gifts'])
    # A modest shaped entrance, with no new doorway inside the public walk core.
    for x in (8,10):
        p.put(x,0,12,'minecraft:stone_bricks',role='proper stone foot below the entrance post')
        for y in (1,2,3):p.put(x,y,12,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y')
        p.put(x,3,13,'mythrais:curved_corbel_dark_oak',facing='south',shape=0)
    for x in range(8,11):p.slab(x,4,12)
    p.lamp(9,3,12,'south')
    # The household is an actual separate tucked room, with a wide open arch
    # rather than furniture placed in a nominal facade shell.
    for z in range(1,6):
        for y in (1,2,3):p.put(6,y,z,'dawnoftimebuilder:charred_spruce_timber_frame')
    for z in (6,7):
        for y in (1,2):p.put(6,y,z,'minecraft:air')
    for z in (2,6):
        for x in range(7,13):p.beam(x,4,z,'x',role='actual exposed potting-room rafter')
    for z in (3,7):
        for x in range(1,5):p.slab(x,3,z,role='shallow home ceiling coffer')
    # Native lanterns have known real emitted light, not just a bright texture.
    for x,z in ((9,2),(9,6)):
        p.put(x,4,z,'minecraft:dark_oak_planks')
        p.put(x,3,z,'minecraft:lantern',hanging=True,waterlogged=False,role='real warm flower/work task light')
        p.supports.append({'detail':[x,3,z],'support':[x,4,z],'role':'normal hanging lantern under an authored full rafter'})
    p.put(2,3,4,'minecraft:lantern',hanging=True,waterlogged=False,role='real warm household task light')
    p.supports.append({'detail':[2,3,4],'support':[2,4,4],'role':'normal hanging lantern below the real upper floor'})
    p.put(3,7,4,'minecraft:lantern',hanging=True,waterlogged=False,role='warm upstairs lamp')
    for x in range(1,7):p.put(x,8,4,'minecraft:dark_oak_planks',role='real roof tie spanning between both upper walls')
    p.supports.append({'detail':[3,7,4],'support':[3,8,4],'role':'upper lamp attached to actual roof tie'})
    p.reserve('Florist circulation',[(9,1,z) for z in range(7,12)]+[(x,1,7) for x in range(6,12)]+[(9,1,5),(9,1,6)])
    p.reserve('Home ground circulation',[(x,1,7) for x in range(2,7)]+[(4,1,z) for z in range(2,7)])
    p.reserve('Home upstairs circulation',[(4,5,z) for z in range(2,8)]+[(3,5,7),(3,5,5)])
    # Circulation is openable space, not permission to erase its actual door.
    # Preserve both ordinary native halves after the interior AIR reservation.
    for y,half in ((1,'lower'),(2,'upper')):
        p.put(9,y,11,'mcwdoors:dark_oak_cottage_door',facing='north',half=half,hinge='left',open=False,powered=False)
    p.stair_flight(5,6,0)
    # The shop is dense and trade-specific: actual cutting, water, storage and
    # display. New container models have native defaults, not copied old items.
    for z in (2,3,4):p.counter(8,1,z,'east','andesite',role='working flower-stem and bouquet counter')
    p.put(8,2,3,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='real stem cutting board')
    p.put(7,1,1,'minecraft:crafting_table',role='real flower wrapping/tool bench')
    p.put(8,1,1,'minecraft:water_cauldron',level=3,role='actual contained clean water for stems')
    p.put(10,1,1,'farmersdelight:dark_oak_cabinet',facing='south',open=False,role='new empty florist tool cabinet')
    p.put(7,1,8,'minecraft:barrel',facing='up',open=False,role='new empty potting material barrel')
    p.shelf(10,2,9,'north',books=True)
    p.put(10,1,8,'handcrafted:terracotta_medium_pot',role='spare hand-thrown empty pot')
    for n,z in enumerate(range(2,6)):
        p.counter(11,1,z,'west','dark_oak_planks',role='deep fancy-window plant display sill')
        p.put(11,2,z,POTS[n],role='real contained display flower/green')
    for n,x in enumerate((7,8,10,11)):
        p.counter(x,1,10,'north','andesite',role='hooked potting room’s return display')
        p.put(x,2,10,POTS[4+n],role='real contained return-display plants')
    for x,y,z,plant in ((7,1,5,POTS[9]),(10,1,6,POTS[4]),(10,1,9,POTS[1]),(7,1,9,POTS[5])):
        p.slab(x,y-1,z);p.put(x,y,z,plant,role='contained flower grouping outside circulation')
    # A narrow supported wooden trellis/plant screen, not loose leaf blocks or
    # unbounded vines, distinguishes the little hooked front work yard.
    for x in (7,11):
        for y in (1,2,3):
            p.put(x,y,12,'minecraft:dark_oak_trapdoor',facing='south',half='top',open=True,powered=False,waterlogged=False,role='fixed wooden slatted plant trellis')
        p.beam(x,4,12,'z',wood='dark_oak',role='modeled trellis top bracket')
    # Ground-floor home: hearth/pantry/dining and reading corner, all reachable.
    p.put(1,1,3,'minecraft:smoker',facing='east',lit=False,role='real small home cooking hearth')
    p.counter(1,1,4,'east');p.put(1,2,4,'handcrafted:wood_cup',facing='east',pieces=2,waterlogged=False,role='cups beside the kitchen hearth')
    p.put(1,1,6,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='new empty household pantry')
    p.table(2,1,5,'east');p.shelf(1,2,2,'east',books=True)
    p.put(2,1,8,'handcrafted:dark_oak_bench',facing='north',shape='single',color='brown',waterlogged=False,role='small reading seat beneath the planted gallery')
    p.put(3,1,8,'handcrafted:dark_oak_side_table',facing='north',color='none',waterlogged=False,role='low home side table')
    p.put(3,2,8,'fishofthieves:potted_tropical_red_fern',role='real contained home greenery')
    # Sleeping/ledger loft is not an empty inaccessible upstairs.
    p.bed(2,5,4)
    p.put(1,5,2,'handcrafted:dark_oak_nightstand',facing='south',color='none',waterlogged=False,role='bedside locker')
    p.put(2,5,6,'handcrafted:dark_oak_desk',facing='south',color='none',waterlogged=False,role='household order and botanical drawing desk')
    p.put(2,6,6,'handcrafted:stackable_book',facing='south',books=3,seed=13,role='flower orders and sketchbooks')
    p.put(1,5,6,'handcrafted:dark_oak_chair',facing='east',color='brown',waterlogged=False,role='loft desk chair')
    p.put(1,5,5,'fishofthieves:potted_tropical_monstera',role='real contained bedroom greenery')
    for x,plant in ((2,POTS[2]),(3,POTS[8])):
        p.slab(x,4,9);p.put(x,5,9,plant,role='contained upper window flowers on supported ledge')
        p.supports.append({'detail':[x,4,9],'support':[x,4,8],'role':'upper planting shelf connected to the real home jetty floor'})
    p.room('Salt & Petal flower/work room',0,(9,1,8),'Deep fancy-glass flower display, real potting/cutting tools, clean water, native plant pots, cupboards, shelving, trellis and warm task lamps.')
    p.room('The florist’s kitchen and parlour',0,(3,1,7),'A separate framed room with actual hearth, pantry, supper table, books, reading seat and contained greenery.')
    p.room('The florist’s upstairs home',4,(3,5,7),'A real stair leads to the bed, bedside locker, order desk, books and planted projecting window beneath a shaped weathered roof.')
    p.features[NAME]=['One original hooked low shop with attached taller home','Deep four-wide proud fancy-glass display and glazed return cheeks','Uneven height/roof rhythm with actual carved window supports and visible shallow ceiling ribs','Potted mod flowers/greens; no uncontrolled sapling/tree/vine growth or invented planter NBT','Separate real workroom/home/loft scenes, not a facade museum']
    p.owner='Salt & Petal doorway approach'
    for x in range(8,11):
        for z in (12,13):
            if z==12 and x in (8,10):continue
            p.put(x,-1,z,'minecraft:andesite')
    p.route('Small doorstep public approach',[(9,1,12),(8,0,13),(9,0,13),(10,0,13)],kind='public-two-wide')
    p.join_derivations=canonical_joins(p)
    return p


def check(p):
    rules=require_material_rule({q:s for q,s in p.blocks.items() if p.owners[q]==NAME},'COMPLETE original Salt & Petal, all rooms/floors/roofs')
    outdoor=require_outdoor_rule({q:s for q,s in p.blocks.items() if p.owners[q]!=NAME},'Salt & Petal tiny actual doorstep')
    errors=[]
    for r in p.routes:
        for x,y,z in r['positions']:
            for h in (0,1):
                s=p.blocks.get((x,y+h,z),'minecraft:air')
                if s!='minecraft:air' and not key(s).endswith('_door'):errors.append((r['id'],[x,y+h,z],s))
            if r['kind']!='stairs' and p.blocks.get((x,y-1,z),'minecraft:air')=='minecraft:air':errors.append((r['id'],[x,y-1,z],'No real walking support'))
    if errors:raise UserError('Keep true human circulation clear: '+str(errors[:10]))
    for row in p.entries:
        x,y,z=row['door']
        for dy,part in ((0,'lower'),(1,'upper')):
            s=p.blocks.get((x,y+dy,z),'minecraft:air')
            if not key(s).endswith('_door') or 'half='+part not in s:raise UserError('The declared usable door must actually retain both native halves')
    for row in p.supports:
        if p.blocks.get(tuple(row['support']),'minecraft:air')=='minecraft:air':raise UserError('A real lamp/window/plant ledge needs its authored support: '+str(row))
    plants=[q for q,s in p.blocks.items() if key(s).startswith(('minecraft:potted_','fishofthieves:potted_'))]
    for x,y,z in plants:
        if p.blocks.get((x,y-1,z),'minecraft:air')=='minecraft:air':raise UserError('A contained real plant pot requires its actual sill/table/floor')
    if len(plants)<16 or len(p.rooms)!=3:raise UserError('Keep the intended rich plant display and all three distinct inhabited scenes')
    return {'targets':len(p.blocks),'material_rule':rules,'outdoor_rule':outdoor,'rooms':3,'contained_real_plant_blocks':len(plants),
        'purposeful_surviving_objects':len({tuple(r['position']) for r in p.props if key(p.blocks.get(tuple(r['position']),'minecraft:air'))==r['block']}),
        'route_samples':sum(len(r['positions']) for r in p.routes),'source_only':True,'native_walk_render_survival_and_art_acceptance':'PENDING'}


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(4*MIB,16*MIB);memory=reader_budget()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private unused-headland source only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or (receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha) or 'stopped' not in receipt.get('scope','').lower():raise UserError('Explicit current stopped source checkpoint required')
    registry=read_json(home/'dashboard/settlement/registry.json');p=construct(registry);ox,oy,oz=p.origin
    jar=home/'server/mods'/FOT_JAR[0]
    if not 0<jar.stat().st_size<4*MIB or digest(jar)!=FOT_JAR[1]:raise UserError('Exact pinned native potted-mod artifact required')
    with zipfile.ZipFile(jar) as archive:
        b=archive.read(FOT_POTTED_REGISTRAR['class'])
        if hashlib.sha256(b).hexdigest()!=FOT_POTTED_REGISTRAR['sha256'] or b'net/minecraft/world/level/block/FlowerPotBlock' not in b:raise UserError('Exact primary native pot registration witness changed')
    world={(x+ox,y+oy,z+oz):s for (x,y,z),s in p.blocks.items()}
    keep=set()
    for rel,sha in (HALL,W3,ZIP):
        if digest(home/rel)!=sha:raise UserError('Frozen hall/W3/zipline custody changed')
        keep.update(flatten(read_json(home/rel)))
    for label,rel,sha in REJECTED:
        if digest(home/rel)!=sha:raise UserError('Preserve old house/BE custody')
        keep.update(flatten(read_json(home/rel)))
    if set(world)&keep:raise UserError('One unused florist may not alter any hall/W3/zipline/rejected-house source, including its AIR')
    if digest(home/FOREST[0])!=FOREST[1]:raise UserError('Exact next28 native woodland reservation required')
    forest={tuple(q) for q in read_json(home/FOREST[0])['all_growth_excluded_columns_xz']}
    if any((x,z) in forest for x,y,z in world):raise UserError('Preserve future southern native growth fields/crowns')
    protected,_=__import__('tools.artistic_north_bank_east',fromlist=['preservation']).preservation(home,registry)
    if any((x,z) in protected for x,y,z in world):raise UserError('Original accepted town/bridge source stays intact')
    terrain=NorthTerrain(home,receipt,registry);before={};supports={};dry=[];footings=[]
    try:
        for x,z in sorted(p.main[NAME]):
            row=terrain.column(x+ox,z+oz);sy=row.get('surface_y');q=(x+ox,sy,z+oz) if sy is not None else (x+ox,oy-1,z+oz)
            if row['kind']!='dry' or sy not in (oy-2,oy-1) or key(terrain.state(*q)) not in GROUND:raise UserError('Florist main foundation must remain actual dry FULL land within its shallow one-metre beach relief: '+str((q,row)))
            below=(q[0],q[1]-1,q[2]);s=terrain.state(*below)
            if s is None or key(s) not in GROUND:raise UserError('Preserve natural thin gravel/hollow; do not support a new florist on it: '+str((q,s)))
            supports[q]=terrain.state(*q);supports[below]=s;dry.append(list(q))
            cells=p.main[NAME]
            if sy==oy-2 and ((x,z) in edge(cells) or x%4==0):
                post=(x+ox,oy-1,z+oz)
                if terrain.state(*post)!='minecraft:air' or post in terrain.entities:raise UserError('A shallow new foundation may replace only actual AIR above its existing dry soil')
                if (x,z-1) not in cells or (x,z+1) not in cells:material='minecraft:andesite'
                elif (x,z) in edge(cells):material='minecraft:stone_bricks'
                else:material='minecraft:cobblestone'
                p.owner=NAME;p.put(x,-1,z,material,role='one-block stone skirt/joist pier on retained natural dry soil')
                world[post]=p.blocks[x,-1,z];footings.append({'position':list(post),'retained_support':list(q),'material':material})
        # The small threshold and its two post feet need the same real dry
        # support proof as the house, rather than assuming an exterior prop is
        # founded just because its block does not fall in Minecraft.
        for x,z in ((8,12),(9,12),(10,12),(8,13),(9,13),(10,13)):
            q=(x+ox,oy-1,z+oz);row=terrain.column(q[0],q[2]);s=terrain.state(q[0],q[1]-1,q[2])
            if row['kind']!='dry' or row['surface_y'] not in (oy-2,oy-1) or s is None or key(s) not in GROUND:raise UserError('A real dry supported doorway approach is required')
            supports[q[0],q[1]-1,q[2]]=s
        proof=check(p)
        for n,q in enumerate(sorted(world,key=lambda p:(p[0]//16,p[2]//16,p[1],p[0],p[2]))):
            actual=terrain.state(*q)
            if actual is None or q in terrain.entities:raise UserError('All new body/roof/approach cells must be saved FULL with no old BE')
            if key(actual) not in VOIDS|SOFT|GROUND|NORTH_SOFT or 'waterlogged=true' in actual:raise UserError('Preserve actual object/water/plant/player work: '+str((q,actual)))
            before[q]=actual
            if n%256==0:reader_budget()
        sources=terrain.snapshot.sources
    finally:terrain.close()
    # This is intentionally NOT the native-settlement format. Root reviews the
    # actual held W3 refinement first, then supplies a new current native before.
    doc={'format':'awft-one-florist-SOURCE-ONLY:1','name':NAME,'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
        'source_sha256':digest(Path(__file__)),'origin':list(p.origin),'blocks':[[*q,s] for q,s in sorted(world.items())],
        'sign_tags_only':[[x+ox,y+oy,z+oz,t] for (x,y,z),t in sorted(p.tags.items())],
        'actual_complete_before':[[*q,s] for q,s in sorted(before.items())],'retained_actual_dry_supports':[[*q,s] for q,s in sorted(supports.items())],
        'actual_main_dry_columns':dry,'shallow_supported_beach_footings':footings,'proof':proof,'rooms':p.rooms,'features':p.features,'routes':p.routes,'supports':p.supports,
        'plant_palette':dict(Counter(key(s) for s in p.blocks.values() if key(s).startswith(('minecraft:potted_','fishofthieves:potted_')))),
        'pinned_mod_plant_jar':FOT_JAR,'pinned_registration_byte_witness':FOT_POTTED_REGISTRAR,
        'held_exact_masks':{'hall':HALL,'W3':W3,'placed_v2':ZIP,'next28forest':FOREST},'raw_saved_sources':sources,'reserve_guard':reserve,'reader_budget':memory,
        'construction_forbidden':True,'native_plan':False,'wider_replication':False,'native_actions':0,'world_writes':0,'existing_BE_or_item_targets':0,
        'next_gates':['Review actual W3 photo-refinement before choosing this single distinct building','Pin/review normal potted species/survival and exact native joining expectations','Rebind current stopped complete before/supports after construction/forest transactions','Parent native before/one prototype/normal joins/strict fullverify, then actual shop/home/shore/roof views','No invented inventory/ownership/NBT and no source result called visual acceptance']}
    raw=(json.dumps(doc,separators=(',',':'))+'\n').encode()
    if len(raw)>16*MIB:raise UserError('Bounded single-florist output exceeded')
    out=home/'staging'/('salt-petal-florist-SOURCE-ONLY-'+str(time.time_ns()));out.mkdir();(out/'source-only.json').open('xb').write(raw)
    return {'folder':str(out),'sha256':digest(out/'source-only.json'),'proof':proof,'native_actions':0,'native_plan':False}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True);args=a.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
