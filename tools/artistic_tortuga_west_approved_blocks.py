"""Small occupied West frontages inside the owner-reviewed whole-city plan.

Earlier recipes, source bundles and actual construction deltas stay immutable.
This additive producer reads the current stopped checkpoint and preserves the
three queued coastal masses as well as the first five actually placed homes.
No running game, world, inventory, entity, native request or deployment is edited.
"""
from __future__ import annotations
import argparse, hashlib, json, time
from contextlib import contextmanager
from pathlib import Path

from control_room.common import UserError, digest, read_json
from tools import artistic_tortuga_coast_batches as coast
from tools import artistic_tortuga_fill as fill
from tools.artistic_tortuga_frontages import RECIPES, AIR, POTS, check, key, base, rect, routes, window, bay_south, joists, light, upper_home
from tools.artistic_west_r2_frontage import canonical_joins
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import native_payload
from tools.playtest import guard

MIB = 1024**2
COAST_SOURCE_SHA = '3b448307cbd842d95faf405a1cd15a9ef20131bf68c974b2d958c5b88080cdc2'
QUEUED = (
 ('staging/tortuga-fill-bent-ropewalk-coast-1793211126478817700/manifest.json', '1cfec91ed478a49a5eea53e3ee6c8aec72ecc1a642f0fd397f713b204632069f'),
 ('staging/tortuga-fill-leaning-galley-hook-1793211150053264700/manifest.json', '1c0d5bb1ca3c46a1232aad6e473e8fdbbe088d40dd6ecf2334ab0bd70a429c14'),
 ('staging/tortuga-fill-tide-stove-west-quay-1793211157736738700/manifest.json', '1e6947baa291649295a6b27a7414b42cac7cc2598cf8329070a6755f7d608e48'),
)
ORIGINAL = {name: RECIPES[name] for name in ('netmender', 'needlewake', 'moon-rigging', 'gull-tackle')}


def new_air(p, x, y, z, name, *, role, **props):
    if p.blocks.get((x,y,z), AIR) != AIR:
        raise UserError('Keep the complete existing recipe furniture and architecture: '+str((p.owner,x,y,z)))
    p.put(x,y,z,name,role=role,**props)


def moon_workroom(registry):
    p = ORIGINAL['moon-rigging'](registry)
    new_air(p,1,1,6,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='real instrument fitter’s closed native-default parts cupboard')
    coast.wall_shelf(p,1,2,6,'east','backed instrument-repair manuals and small fitting orders')
    new_air(p,2,3,1,'mcwlights:tavern_wall_lantern',facing='south',role='small working chart and fitting-table light')
    p.supports.append({'detail':[2,3,1],'support':[2,3,0],'role':'chart light attached to its real north workshop wall'})
    canonical_joins(p)
    return p


def tackle_workroom(registry):
    # The old proud porch would reduce the actual alley to one block.
    # This NEW unplaced variant recesses its cheeks and door inside its
    # own main mass; no existing house or high corbel is shortened.
    m=rect(0,0,7,8)-{(0,0),(0,1),(7,0)}
    u=rect(0,1,4,7)|{(1,8),(2,8),(3,8)}
    p=base(registry,'Gull Tackle Recessed Return',m,u,up='minecraft:green_terracotta')
    p.roof((-1,0,5,9),8,(0,1,2,3,2,1,0),family='dark_oak',hip_south=True)
    p.roof((4,-1,8,8),4,(0,1,2,1,0),family='spruce',annex=True)
    routes(p,'Gull Tackle recessed return',[(3,z)for z in range(2,8)]+[(x,7)for x in range(3,8)],[(3,z)for z in range(2,7)]+[(2,5)],stairs=(4,6))
    window(p,7,1,2,'east',width=3,height=2);window(p,0,1,3,'west',width=2);bay_south(p,1,8)
    window(p,0,5,3,'west',width=2);joists(p,1,3,(3,6));joists(p,1,3,(3,6),4)
    p.counter(1,1,3,'east',role='actual tackle and twine packing bench')
    p.put(1,2,3,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='actual cork and line cutting board')
    p.put(1,1,2,'minecraft:barrel',facing='up',open=False,role='new native-default tackle supplies, no copied Items')
    p.put(2,1,2,'minecraft:crafting_table',role='real hook and float fitting station')
    p.put(6,1,2,'minecraft:water_cauldron',level=3,role='contained tackle-rinsing water')
    p.shelf(5,2,6,'north',books=True)
    p.put(1,1,6,'handcrafted:dark_oak_chair',facing='east',color='brown',waterlogged=False,role='angler’s waiting and repair seat')
    p.put(6,1,6,POTS[7],role='contained blue orchid beside the recessed doorway')
    light(p,2,3,4,'small real tackle-work task lantern')
    upper_home(p,bed=(1,4),desk=(1,6),chair=(2,6),chair_face='west',hearth=(1,7),pantry=(2,7),table=(2,2),standing=(3,5),title='Fisher’s sheltered sleeping loft')
    for z in(6,8):
        for y in(1,2,3):p.put(7,y,z,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y',role='actual rooted recessed-entry cheek inside the main footprint')
        p.put(8,3,z,'mythrais:curved_corbel_dark_oak',facing='east',shape=0,role='small high entry bracket above the full two-high alley body')
    for z in(6,7,8):p.beam(7,4,z,'z',wood='dark_oak',role='real lintel above the recessed doorway')
    for y,half in((1,'lower'),(2,'upper')):p.put(6,y,7,'mcwdoors:dark_oak_cottage_door',facing='west',half=half,hinge='left',open=False,powered=False)
    p.entries.append({'owner':p.owner,'door':[6,1,7],'outward':'east','outside_step':[7,0,7]})
    p.sign(8,3,5,'east',['Gull Tackle','Twine • Fittings']);p.put(7,3,5,'minecraft:dark_oak_planks')
    p.room('Recessed tackle packing and fitting shop',0,(3,1,5),'Real cutting/fitting tools, contained rinse water, packing bench, backed accounts, tool cupboard and repair seat beside a deep door that leaves the alley open.')
    new_air(p,6,1,5,'farmersdelight:dark_oak_cabinet',facing='west',open=False,role='actual tackle-sorter’s small native-default tool cupboard')
    coast.wall_shelf(p,6,2,5,'west','backed hook-pattern and repair-account shelf')
    canonical_joins(p)
    return p


def chart_loft(registry):
    """A genuinely shallow ten-wide frontage, with instruments below a home."""
    p = coast.kettle_loft(registry)
    expected = {(1,1,4):'minecraft:smoker', (3,2,1):POTS[4], (3,1,2):'minecraft:water_cauldron'}
    for q,ident in expected.items():
        if key(p.blocks.get(q,AIR)) != ident:
            raise UserError('The frozen shallow-house recipe changed; do not silently replace a different object')
    p.put(1,1,4,'minecraft:cartography_table',role='real chart correction and copying station below the glazed home')
    p.put(3,2,1,'supplementaries:globe',facing='east',powered=False,rotation=0,waterlogged=False,role='native unpowered globe on the actual instrument-fitting bench')
    p.put(3,1,2,'minecraft:barrel',facing='up',open=False,role='new native-default instrument-order stock; no fabricated Items')
    new_air(p,3,2,2,'supplementaries:hourglass',facing='up',light_level=0,waterlogged=False,role='ordinary native watchglass on the real full barrel top')
    new_air(p,1,1,3,'minecraft:dark_oak_planks',role='small full-depth chart-window display plinth')
    new_air(p,1,2,3,POTS[4],role='contained fern on the actual fixed display plinth')
    for room in p.rooms:
        if room['floor'] == 0:
            room['name'] = 'Chart and instrument workshop'
            room['story'] = 'Actual cartography and fitting benches, native globe, watchglass, accounts and contained fern beneath a shallow occupied loft.'
    canonical_joins(p)
    return p


EXTRA = {'west-moon-workroom':moon_workroom,'west-tackle-workroom':tackle_workroom,'west-chart-loft':chart_loft}


@contextmanager
def source_recipes():
    """Only new source-local keys; original registry always restored."""
    if set(EXTRA)&set(RECIPES):
        raise UserError('Do not overwrite a frozen recipe or persist a new registry entry')
    RECIPES.update(EXTRA)
    try:
        yield
    finally:
        for name in EXTRA: RECIPES.pop(name,None)


BATCHES = {
 'net-needle-crook': {
  'buildings': (
   {'recipe':'netmender','turn':3,'name':'The Cork & Needle','trade':'Nets • Corks • Repairs','origin':(1008,63,-1253)},
   {'recipe':'needlewake','turn':0,'name':'The Mended Wake','trade':'Cloth • Sea Coats • Home','origin':(1009,63,-1278)},
  ),
  'links': (
   ('Net workshop’s short inland threshold',((1018,-1251),(1021,-1251))),
   ('Dressmaker’s short new approach meets retained quay paving',((1018,-1273),(1020,-1273))),
  ),
  'design':'Two different occupied proportions on the actual dry western shore: a long net workroom opens inland and a taller cloth home tucks into the northern hook. They preserve the retained working buildings and use small real entrances rather than vacant broad courts.',
  'street_views': (
   ('Cork-and-needle inland frontage',(1019.5,64,-1250.5),(1014,67,-1249)),
   ('Mended Wake cloth-shop frontage',(1019.5,64,-1272.5),(1013,68,-1272)),
  ),
 },
 'moon-tackle-returns': {
  'buildings': (
   {'recipe':'west-moon-workroom','turn':2,'name':'Moonwatch Fittings','trade':'Charts • Instruments • Home','origin':(1090,63,-1272)},
   {'recipe':'west-tackle-workroom','turn':0,'name':'The Gull’s Last Hook','trade':'Tackle • Repairs • Home','origin':(1073,63,-1239)},
  ),
  'links': (
   ('Moonwatch’s narrow eastern service return',((1098,-1271),(1098,-1260))),
   ('Tackle-house shared two-wide alley below retained high corbels',((1081,-1233),(1081,-1230))),
  ),
  'design':'A crooked navigation oriel and smaller tackle workshop face two different intimate alleys. Actual work cupboards, manuals, repair benches and a warm task light supplement fully furnished homes. No corbel, stock, flight envelope or existing shop is moved for the shared low walking passage.',
  'street_views': (
   ('Moonwatch fitting-house face',(1099.5,64,-1266.5),(1092,69,-1266)),
   ('Tackle-house from the genuine low alley',(1082.5,64,-1230.5),(1077,67,-1234)),
  ),
 },
 'chart-window-loft': {
  'buildings': ({'recipe':'west-chart-loft','turn':1,'name':'The Small Meridian','trade':'Charts • Watchglasses • Home','origin':(1041,63,-1230)},),
  'links': (('Small Meridian’s tiny north approach beside the retained trades',((1048,-1232),(1048,-1233))),),
  'design':'A shallow ten-wide chart frontage and occupied projecting home fit a narrow existing strip. Its real instrument bench, native globe, chart station, watchglass and supported fern are composed as a specific trade, rather than another renamed food shop.',
  'street_views': (('Small Meridian north-facing recessed frontage',(1048.5,64,-1232.5),(1046,67,-1227)),),
 },
}

# The stopped field already observes these real public pavers. They are
# verification context, not construction ownership and never replacement.
RETAINED_APPROACH = {'net-needle-crook':((1018,-1271),(1018,-1270),(1019,-1271),(1019,-1270))}


def retained_approach(rows,batch,prior,new_targets):
    observed = {tuple(r[:2]):r for r in rows}
    result = {}
    for x,z in RETAINED_APPROACH.get(batch,()):
        row = observed.get((x,z))
        if row is None: raise UserError('Retain the exact saved public approach; do not invent a paver')
        for y in (63,64,65):
            q = (x,y,z);value = row[y-61]
            if q in new_targets: raise UserError('An unchanged public approach must never be in the construction delta')
            if q in prior and prior[q] != value: raise UserError('Retained public approach disagrees with its actual authored source')
            result[q] = value
    return result


def construction_targets(home, refs):
    targets = {}; provenance = []; buildings = []
    for rel,sha in refs:
        if digest(home/rel) != sha: raise UserError('An exact retained construction manifest changed')
        manifest = read_json(home/rel)
        path = home/Path(rel).parent/'cluster-PROPOSAL.json'
        if digest(path) != manifest['files'][path.name]['sha256']:
            raise UserError('Preserve the actual construction delta, never infer ownership from a verification context')
        for q,value in flatten(read_json(path)).items():
            if q in targets and targets[q] != value: raise UserError('Retained construction sources disagree')
            targets[q] = value
        buildings.extend(manifest['buildings'])
        provenance.append({'relative':str(path.relative_to(home)),'sha256':digest(path),'ownership':'construction delta only; full verification context confers no ownership'})
    return targets,provenance,buildings


def shared_low_walk(original_rows, prior):
    """Specific existing low passage only; no added buildable land authority."""
    original = {tuple(r[:2]):r for r in original_rows}
    result = []
    for x in (1081,1082):
        for z in range(-1233,-1228):
            row = original.get((x,z))
            if row is None: raise UserError('Shared alley requires its exact current FULL saved walking witness')
            for y in (63,64,65):
                q = (x,y,z)
                if q in prior:
                    # Never pave an old source-owned floor or clear a retained body.
                    if y == 63 or prior[q] != AIR or row[y-61] != AIR:
                        raise UserError('Keep the retained floor, solid, fixture and inventory from the shared alley')
            result.append(row)
    return result


def subset_field(home,checkpoint_id,checkpoint_sha,field_path,field_sha,batch):
    guard(0,32*MIB)
    home = fill.private_home(home)
    if digest(Path(coast.__file__)) != COAST_SOURCE_SHA:
        raise UserError('Keep the frozen original coastal producer unchanged')
    path,sha = coast.derived_field(home,checkpoint_id,checkpoint_sha,field_path,field_sha)
    data = read_json(path)
    queued,refs,buildings = construction_targets(home,QUEUED)
    first,first_refs,_ = construction_targets(home,coast.FIVE)
    excluded = {(x,z)for x,y,z in queued if 63<=y<=85}
    data['eligible_columns_READONLY'] = [r for r in data['eligible_columns_READONLY']if tuple(r[:2])not in excluded]
    walking = {tuple(r[:2]):r for r in data['two_high_walk_columns_READONLY']if tuple(r[:2])not in excluded}
    if batch == 'moon-tackle-returns':
        for row in shared_low_walk(read_json(field_path)['two_high_walk_columns_READONLY'],{**first,**queued}):
            walking[tuple(row[:2])] = row
    data['two_high_walk_columns_READONLY'] = list(walking.values())
    for row in buildings: data['retained_source_main_footprints']['queued coastal '+row['name']] = row['main_columns_xz']
    data.update(approved_blocks_source_sha256=digest(Path(__file__)),queued_construction_sources=refs,
      shared_low_alley_walk_only=batch=='moon-tackle-returns',added_buildable_authority_columns=0,
      eligible_columns=len(data['eligible_columns_READONLY']))
    raw = (json.dumps(data,separators=(',',':'))+'\n').encode()
    if len(raw)>16*MIB: raise UserError('Finite16MiB subtract-only field cap exceeded')
    out = home/'staging'/('tortuga-approved-blocks-subset-'+str(time.time_ns()));out.mkdir()
    (out/'field-READONLY.json').open('xb').write(raw)
    return out/'field-READONLY.json',digest(out/'field-READONLY.json'),{**first,**queued},first_refs+refs


def prepare_batch(home,checkpoint_id,checkpoint_sha,field_path,field_sha,batch):
    if batch not in BATCHES: raise UserError('An exact finite authored batch is required')
    guard(8*MIB,96*MIB)
    home = fill.private_home(home)
    field_path = Path(field_path)
    subset,sha,prior,refs = subset_field(home,checkpoint_id,checkpoint_sha,field_path,field_sha,batch)
    with source_recipes():
        registry = read_json(home/'dashboard/settlement/registry.json')
        states,tags,_,_ = fill.modeled(registry,BATCHES[batch])
        collisions = sorted(set(states)&set(prior))
        if collisions: raise UserError('Preserve every actual/queued earlier construction target: '+str(collisions[:8]))
        if len(states)+2048>12000: raise UserError('Keep the finite native batch below12K targets')
        result = fill.prepare(home,checkpoint_id,checkpoint_sha,subset,sha,batch,definition=BATCHES[batch],definition_source=Path(__file__))
    folder = Path(result['folder']);manifest = read_json(folder/'manifest.json')
    if manifest['targets']>12000: raise UserError('Retain artifact but refuse native admission above12K targets')
    new_targets = flatten(read_json(folder/'cluster-PROPOSAL.json'))
    collisions = sorted(set(new_targets)&set(prior))
    if collisions: raise UserError('Retain artifact but never admit a public lane over earlier construction: '+str(collisions[:8]))
    approach = retained_approach(read_json(field_path)['two_high_walk_columns_READONLY'],batch,prior,new_targets)
    if approach:
        for filename in ('before-VERIFY-ONLY.json','complete-after-VERIFY-ONLY.json'):
            old = read_json(folder/filename);values = flatten(old)
            if any(q in values and values[q] != value for q,value in approach.items()):
                raise UserError('Keep the exact unchanged public pavers/body in before and full verification')
            values.update(approach)
            doc = native_payload(registry,values,checkpoint_sha,'VERIFY ONLY — unchanged public pavers and the complete new occupied frontage',tags=tags if filename.startswith('complete')else None)
            doc.update(construction_forbidden=True,verification_only=True)
            raw = (json.dumps(doc,separators=(',',':'))+'\n').encode()
            (folder/filename).write_bytes(raw)
            manifest['files'][filename] = {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        manifest['retained_public_approach'] = {'field_sha256':field_sha,'columns_xz':[list(q)for q in RETAINED_APPROACH[batch]],'actual_before_states':len(approach),'construction_ownership':False,'replacement_or_clearance_writes':0}
    map_bytes = coast.batch_map(manifest,read_json(subset))
    if len(map_bytes)>MIB: raise UserError('Finite1MiB source-map cap exceeded')
    (folder/'batch-map-PLAN-ONLY.svg').open('xb').write(map_bytes)
    manifest['files']['batch-map-PLAN-ONLY.svg'] = {'sha256':hashlib.sha256(map_bytes).hexdigest(),'bytes':len(map_bytes),'tier':'SOURCE PLANNING ONLY; fresh native before/after map and actual photos still required'}
    manifest.update(native_target_cap=12000,earlier_construction_keepouts=refs,
      approved_west_concept={'relative':coast.APPROVED[0],'sha256':coast.APPROVED[1]},frozen_coastal_source_sha256=COAST_SOURCE_SHA)
    (folder/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n',encoding='utf-8')
    result.update(manifest_sha256=digest(folder/'manifest.json'),files=manifest['files'])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True);parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True)
    parser.add_argument('--field',type=Path,required=True);parser.add_argument('--field-sha',required=True);parser.add_argument('--batch',choices=BATCHES,required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_batch(args.home,args.checkpoint_id,args.checkpoint_sha,args.field,args.field_sha,args.batch),indent=2))
