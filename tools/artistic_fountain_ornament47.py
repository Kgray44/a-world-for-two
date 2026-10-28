"""Photo-led additive carved fountain cornices; no operating-world authority.

Only six wall-backed stacks and two contained fern pots are proposed. The
functional47 fountain is WET; historical575 witnesses are explicitly historical,
never a replacement dry precondition or permission to replay the whole fountain.
"""
from __future__ import annotations

import argparse
from itertools import product
import hashlib
import json
import math
import os
from pathlib import Path
import zipfile

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_bridge_refinement import encoded
from tools.artistic_fountain_centerpiece import (CURB, WATER_CROSS, OUTPUT_PATH,
    MARS, control_positions, decode)
from tools.artistic_fountain_dry_binding import SOURCE, SOURCE_GEOMETRY
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_spawn_plaza import AIR, DIR
from tools.artistic_spawn_plaza import JET_WITNESSES, STOP_LEVER, state
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, base

MIB = 1024**2
CHECKPOINT = '20261028T061123Z-575aff'
CHECKPOINT_SHA = '2633518e1a31a262b8f209e33bfeb9d0a15e431b150a98d05334e9c33d9508ad'
MAX_OUTPUT = 8*MIB
NATIVE_FUNCTION = 'dashboard/settlement/fountain-result-f419b47b-32e5-44ae-b766-8fe5fb8a6dd1.json'
NATIVE_FUNCTION_SHA = 'e7bf4ff1675f2e028fdac46b21b9930777731a3051ad6f1af1612bb5455572fb'
VIEWS = ('logs/visual-review/r47-review-b/fountain-flow.png',
         'logs/visual-review/r47-review-c/fountain-upper-quarter.png')
# Position is the lower wall applique, backing vector points INTO retained wall.
# The small volume is an attached relief, never a detached column or new tower.
STACKS = (
    ((1135,71,-1130), 'west', (1,0,0)), ((1135,71,-1128), 'west', (1,0,0)),
    ((1141,71,-1130), 'east', (-1,0,0)), ((1141,71,-1128), 'east', (-1,0,0)),
    ((1137,71,-1132), 'north', (0,0,1)), ((1139,71,-1132), 'north', (0,0,1)),
)
# Curved-frieze facing names describe a different model convention. Its EAST
# variant has a complete backing strip at localX16 and projects to localX5.
FRIEZE_FACE = {'west':'east', 'east':'west', 'north':'south'}
FULL_MOUNTS = {'minecraft:quartz_bricks', 'minecraft:chiseled_quartz_block',
               'rechiseled:quartz_block_bordered', 'chipped:inlayed_calcite',
               'dawnoftimebuilder:marble', 'dawnoftimebuilder:marble_coffer'}


def recipe(registry):
    additions, mounts, roles = {}, {}, {}
    for start, face, backing in STACKS:
        x,y,z = start
        for n,(block,props) in enumerate((
            ('mythrais:corbel_02_stone', {'colour':'3','facing':face}),
            ('mythrais:corbel_scroll_centre_travertine', {'facing':face,'shape':'0'}),
            ('mythrais:curved_frieze_travertine', {'facing':FRIEZE_FACE[face], 'half':'bottom',
                                               'shape':'straight','waterlogged':False}))):
            p = x,y+n,z
            additions[p] = state(registry, block, **props)
            mounts[p] = tuple(p[i]+backing[i] for i in range(3))
            roles[p] = face+' attached carved relief / volute / curved cornice layer'+str(n)
        p = x,74,z
        additions[p] = state(registry, 'minecraft:waxed_oxidized_cut_copper_slab'
                             if face=='west' else 'dawnoftimebuilder:marble_coffer_slab',
                             type='bottom',waterlogged=False)
        mounts[p] = tuple(p[i]+backing[i] for i in range(3))
        roles[p] = face+' short supported stepped cornice lip; patinated copper only on arrival side'
    for x in (1137,1139):
        p = x,75,-1131
        additions[p] = state(registry,'minecraft:potted_fern')
        mounts[p] = (x,74,-1131)
        roles[p] = 'Contained fern on existing crown corner, away from the unmodified central statue'
    return additions,mounts,roles


def keepout(source,routes):
    fixed = control_positions() | set(OUTPUT_PATH) | CURB | WATER_CROSS
    fixed |= {(1138,y,-1128) for y in (71,72,73)}
    fixed |= {(x,y,z) for x,_,z in JET_WITNESSES for y in range(64,71)}
    fixed |= {(1145,y,z) for y in range(64,71) for z in (-1131,-1130,-1129)}
    fixed |= {(1138,y,-1129) for y in (75,76,77)}
    fixed |= {(x,y,z) for x,floor,z in routes for y in (floor+1,floor+2)}
    # Adding a conductor beside existing redstone can alter the working gate.
    torches = {p for p,s in source.items() if base(s) in
               ('minecraft:redstone_wall_torch','minecraft:redstone_torch')}
    fixed |= {tuple(p[i]+v[i] for i in range(3)) for p in torches for v in DIR.values()}
    return fixed


def validate_additions(source, additions, mounts, forbidden):
    if not additions or len(additions)>32 or set(additions)&forbidden:
        raise UserError('Small ornament must avoid every statue, hydraulic/control/water/route keepout')
    for p,value in additions.items():
        if source.get(p) != AIR:
            raise UserError('Additive ornament requires explicit historical source AIR; never replace the fountain')
        support = source.get(mounts[p])
        if p[1] <= 73 and base(support or '') not in FULL_MOUNTS:
            raise UserError('Wall relief requires retained full marble/quartz backing')
        if p[1] in (74,75) and not (support and 'slab' in base(support) and 'type=top' in support):
            raise UserError('Crown lip or pot needs an explicit retained top-slab mount')
        if base(value).startswith('create:') or base(value)==MARS:
            raise UserError('No machinery or statue writes in an ornament proposal')
    combined = dict(source) | additions
    return {'complete_building':require_material_rule(combined,'Complete R5 fountain plus small carved ornament'),
            'outdoor':require_outdoor_rule(combined,'Full retained fountain/plaza plus small relief'),
            'all_original_solids_and_unselected_AIR_unchanged':all(combined[p]==s for p,s in source.items() if p not in additions)}


def rotate(point,origin,axis,angle):
    p = [point[i]-origin[i] for i in range(3)]
    a=math.radians(angle);c,s=math.cos(a),math.sin(a)
    x,y,z=p
    q = (x,c*y-s*z,s*y+c*z) if axis=='x' else (c*x+s*z,y,-s*x+c*z) if axis=='y' else (c*x-s*y,s*x+c*y,z)
    return [q[i]+origin[i] for i in range(3)]


class Models:
    """Bounded actual asset summaries, not a renderer or native collision proof."""
    def __init__(self,home):
        client = Path(os.environ['APPDATA'])/'PrismLauncher/libraries/com/mojang/minecraft/1.21.1/minecraft-1.21.1-client.jar'
        self.paths = {'minecraft':client,
            'mythrais':home/'server/mods/mythrais-5.2.1-1.21.1-neo-beta5.jar',
            'dawnoftimebuilder':home/'server/mods/dawnoftimebuilder-neoforge-1.21.1-1.6.8.jar'}
        self.archives={}
        self.inputs={}
        for namespace,path in self.paths.items():
            if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=128*MIB:
                raise UserError('Actual bounded registered model archive required')
            self.archives[namespace]=zipfile.ZipFile(path)
            self.inputs[namespace]={'name':path.name,'bytes':path.stat().st_size,'sha256':digest(path)}

    def close(self):
        for archive in self.archives.values():archive.close()

    def get(self,namespace,name):
        member=self.archives[namespace].getinfo(name)
        if not 0<member.file_size<=128*1024:raise UserError('Bounded selected asset required')
        raw=self.archives[namespace].read(member)
        return json.loads(raw),{'member':name,'sha256':hashlib.sha256(raw).hexdigest()}

    def geometry(self,model,seen=None):
        seen=set() if seen is None else set(seen)
        if model in seen or len(seen)>=8:raise UserError('Cyclic/unbounded selected model ancestry')
        seen.add(model)
        namespace,name=model.split(':',1)
        doc,fact=self.get(namespace,'assets/'+namespace+'/models/'+name+'.json')
        if 'elements' in doc:return doc['elements'],[fact]
        if 'parent' not in doc:raise UserError('Selected custom geometry needs native review instead of assumed bounds')
        elements,parents=self.geometry(doc['parent'],seen)
        return elements,[fact]+parents

    def summary(self,value):
        name,_,tail=value.partition('[')
        props=dict(p.split('=',1) for p in tail[:-1].split(',')) if tail else {}
        namespace,name=name.split(':',1)
        doc,blockstate=self.get(namespace,'assets/'+namespace+'/blockstates/'+name+'.json')
        variants=[]
        for key,row in doc.get('variants',{}).items():
            required=dict(p.split('=',1) for p in key.split(',')) if key else {}
            if all(props.get(k)==v for k,v in required.items()):variants.append(row)
        if len(variants)!=1 or isinstance(variants[0],list):
            raise UserError('One deterministic actual model variant required')
        variant=variants[0];elements,chain=self.geometry(variant['model'])
        points=[]
        for element in elements:
            if any(k not in element for k in ('from','to')):raise UserError('Explicit finite model cuboid required')
            for values in product(*zip(element['from'],element['to'])):
                p=list(values)
                r=element.get('rotation')
                if r:
                    p=rotate(p,r['origin'],r['axis'],r['angle'])
                    if r.get('rescale'):
                        for i,axis in enumerate('xyz'):
                            if axis!=r['axis']:p[i]=r['origin'][i]+(p[i]-r['origin'][i])/math.cos(math.radians(r['angle']))
                for axis in ('x','y'):
                    if variant.get(axis):p=rotate(p,(8,8,8),axis,-variant[axis])
                points.append(p)
        bounds=[min(p[i] for p in points)/16 for i in range(3)]+[max(p[i] for p in points)/16 for i in range(3)]
        return {'blockstate':blockstate,'model_chain':chain,'variant':variant,'elements':len(elements),
                'local_visual_bounds':bounds,'native_collision_or_neighbor_shape_acceptance':False}


def intersects(bounds,position):
    return all(bounds[i]<position[i]+1-1e-7 and bounds[i+3]>position[i]+1e-7 for i in range(3))


def plan(registry,field,label):
    palette=sorted(set(field.values()));index={s:n for n,s in enumerate(palette)}
    return {'format':'awft-native-settlement:1','name':label,'seed':registry['seed'],'world_path':registry['world_path'],
        'backup_sha256':CHECKPOINT_SHA,'bounds':[1135,-1132,1141,-1128],'palette':palette,
        'blocks':[[*p,index[s]] for p,s in sorted(field.items())],'block_entities':[],'commands':[],
        'landmarks':[],'construction_forbidden':True,'verification_only':True,
        'validation':'SOURCE PROPOSAL ONLY; current fountain is wet. Fresh native target/mount proof and later wet-snapshot binding required.'}


def prepare(home,output):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.exists() or output.parent!=home/'staging':raise UserError('New private source-only output required')
    reserve=guard(2*MIB,MAX_OUTPUT)
    registry=read_json(home/'dashboard/settlement/registry.json')
    original=home/SOURCE/'plaza.json'
    if digest(original)!=SOURCE_GEOMETRY:raise UserError('Exact built R5 statue/upper body source required')
    source=decode(read_json(original))
    routes_doc=read_json(home/'staging/artistic-spawn-plaza-r2-20261027T2002Z/manifest.json')
    additions,mounts,roles=recipe(registry)
    forbidden=keepout(source,routes_doc['routes'])
    checks=validate_additions(source,additions,mounts,forbidden)
    checkpoint={'id':CHECKPOINT,'sha256':CHECKPOINT_SHA,'verified':True}
    snapshot=BackupWorld(home,checkpoint,registry)
    try:
        before={p:snapshot.state(p) for p in set(additions)|set(mounts.values())}
        if any(before[p]!=AIR or p in snapshot.protected for p in additions):
            raise UserError('Historical575 ornament cell is not ordinary known AIR')
        if any(before[p]!=source[p] for p in set(mounts.values())):
            raise UserError('Historical575 retained mount changed from the authored source')
        sources=list(snapshot.sources)
    finally:snapshot.close()
    models=Models(home)
    try:
        model_facts={s:models.summary(s) for s in sorted(set(additions.values()))}
        for p,s in additions.items():
            b=model_facts[s]['local_visual_bounds'];world=[p[i%3]+b[i] for i in range(6)]
            if any(intersects(world,q) for q in forbidden):
                raise UserError('Actual selected decorative model reaches a functional/statue/route keepout')
        archives=models.inputs
    finally:models.close()
    proof=home/NATIVE_FUNCTION
    marker=proof.with_name(proof.name+'.complete')
    function=read_json(proof)
    if (digest(proof)!=NATIVE_FUNCTION_SHA or marker.read_text().strip()!=NATIVE_FUNCTION_SHA
            or function.get('actual_pump_fill_and_physical_gate_cycle') is not True or function.get('failures')!=0
            or function.get('cleanup_required') is not False or function.get('temporary_tickets_remaining')!=0
            or function.get('pending_shared_chunk_futures')!=0 or function.get('cleanup_errors')!=[]):
        raise UserError('Retain the actual native47 hydraulic success, never invent a new dry state')
    docs={'addition-26-SOURCE-ONLY.json':encoded(plan(registry,additions,'PROPOSAL ONLY six carved cornice stacks and contained ferns')),
          'historical575-targets-and-mounts-VERIFY-ONLY.json':encoded(plan(registry,before,'HISTORICAL575 static target and mount witness; NOT current wet-world admission')),
          'addition-after-VERIFY-ONLY.json':encoded(plan(registry,additions,'PROSPECTIVE26 ornament only; no full dry fountain replay')),
          'selected-models.json':encoded({'archives':archives,'selected':model_facts,'not_a_renderer_or_native_collision_receipt':True})}
    manifest={'format':'awft-photo-led-fountain-ornament47:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'historical_static_checkpoint_id':CHECKPOINT,'historical_static_checkpoint_sha256':CHECKPOINT_SHA,
        'current_fountain_is_wet_after_native47_commission':True,'historical575_is_not_a_current_dry_precondition':True,
        'actual_working_hydraulics_receipt_sha256':NATIVE_FUNCTION_SHA,'working_hydraulics_not_recommissioned_by_this_producer':True,
        'actual_photographs':[{'path':p,'sha256':digest(home/p)} for p in VIEWS],
        'design':'Six attached carved bases and scroll volutes supporting short curved cornices. Two patinated copper lips face arrival; two fern pots remain contained on original crown corners. South maintenance face remains clear.',
        'targets':len(additions),'original_cells_recolored_removed_or_replayed':0,'roles':[{'pos':list(p),'role':roles[p],'retained_mount':list(mounts[p])} for p in sorted(additions)],
        'functional_keepout_cells':len(forbidden),'checks':checks,'models_are_actual_pinned_assets':True,
        'native_model_collision_shape_join_and_art_approval':False,'native_actions':0,'world_writes':0,'native_entity_or_BE_writes':0,
        'source_regions':sources,'reserve_guard':reserve,
        'required_next':['Fresh parent native exact AIR targets and unchanged solid/top-slab mounts',
            'Current wet-world/same exact world checkpoint binding; no dry whole-fountain before replay',
            'Parent-reviewed additive admission, normal shape settlement and strict ornament after verification',
            'Read-only actual fountain wet-flow/control/pipe/statue preservation checks',
            'Actual matching arrival/upper-quarter/east/north views plus night view before artistic acceptance'],
        'files':{name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in docs.items()}}
    docs['manifest.json']=encoded(manifest)
    if sum(map(len,docs.values()))>MAX_OUTPUT:raise UserError('Finite ornament source budget exceeded')
    output.mkdir()
    for name,raw in docs.items():(output/name).write_bytes(raw)
    return {'folder':str(output),'manifest_sha256':hashlib.sha256(docs['manifest.json']).hexdigest(),'targets':len(additions),'native_actions':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.home,args.output),indent=2))
