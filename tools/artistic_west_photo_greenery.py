"""One photo-led alley pocket after the completed six West passes; Source only.

Two clay flowering-bush urns and three irregular leaf swags, never new trees.
Retains all existing blocks, window view cells, signs and actual walking bodies.
"""
from pathlib import Path
import argparse,hashlib,json,time
from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_spawn_plaza import state,payload
from tools.artistic_botanical import STURDY,FACES
from tools.artistic_materials import require_outdoor_rule
from tools.artistic_west_lush_streets import protections,VOIDS,key,leaf_distances,plus
from tools.settlement_attractions import BackupWorld,properties
from tools.playtest import guard

CHECKPOINT=('20261029T023601Z-3ac3e4','224ca7100d06f7b645a996154aa36ea02d9185819250e481d1690fd5f56a4838')
PHOTO='logs/visual-review/tortuga-corrected63-1793243568900581900/west-alley.png'
PHOTO_SHA='cc8476ada59ffddd5b8dfe0295a406cedb5c0f3ea8e61de0eb0ce12b3cf0b7b2'
POTS=((1035,64,-1274),(1035,64,-1273))
SWAGS=(
 ('Court post trained foliage',((1035,67,-1273),(1035,68,-1273),(1035,68,-1272)),((1034,67,-1273),)),
 ('First high alley swag',((1031,70,-1267),(1032,70,-1267),(1032,71,-1267),(1032,70,-1268),(1032,69,-1268)),((1030,70,-1267),(1033,70,-1267))),
 ('Opposite entry canopy return',((1032,70,-1260),(1033,70,-1260),(1032,71,-1260)),((1031,70,-1260),(1034,70,-1260))),
)


def prepare(home):
    home=Path(home).resolve();reserve=guard(2*1024**2,2*1024**2)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Owned artistic home required')
    if digest(home/PHOTO)!=PHOTO_SHA:raise UserError('Original actual photo differs')
    registry=read_json(home/'dashboard/settlement/registry.json')
    companion=read_json(home/'backups'/(CHECKPOINT[0]+'.json'))
    if companion.get('integrity')!='verified'or companion.get('sha256')!=CHECKPOINT[1]:raise UserError('Actual post-six-pass stopped archive required')
    main,transport,walks,custody=protections(home)
    snapshot=BackupWorld(home,{'id':CHECKPOINT[0],'sha256':CHECKPOINT[1],'verified':True},registry)
    before={};delta={};roles={};supports={};routes={};windows=set()
    def add(p,name,role,**props):
        old=snapshot.state(p)
        if p in snapshot.protected or (p[0],p[2])in main|transport or p in delta or key(old)not in VOIDS:
            raise UserError('Only new AIR outside all retained building/transport cells: '+str((p,old)))
        if p[1]in(64,65)and(p[0],p[2])in walks:raise UserError('Keep current public walking body')
        before[p]=old;delta[p]=state(registry,name,**props);roles[p]=role
    try:
        for x in range(1028,1040):
            for z in range(-1276,-1256):
                for y in range(64,73):
                    p=(x,y,z);v=snapshot.state(p)
                    if 'window'in key(v):
                        face=properties(v).get('facing')
                        if face in FACES:
                            for n in(-2,-1,1,2):windows.add(plus(p,FACES[face],n))
        for x,y,z in POTS:
            # The existing full paving rests on an independently literal dry
            # stack; neither its grade nor the underlying ground is rewritten.
            for yy in(63,62):
                p=(x,yy,z);v=snapshot.state(p);supports[p]=v
                if p in snapshot.protected or key(v)in VOIDS|{'minecraft:water'}:raise UserError('Real unchanged dry clay-urn footing required')
            add((x,y,z),'dawnoftimebuilder:big_flower_pot','actual one-metre carved clay urn',waterlogged=False)
            for dy in(1,2):
                add((x,y+dy,z),'minecraft:flowering_azalea_leaves'if(z+dy)%2 else'minecraft:azalea_leaves',
                    'contained flowering bush fill; persistent decoration, no fabricated tree',distance=7,persistent=True,waterlogged=False)
        for label,points,roots in SWAGS:
            for p in roots:
                v=snapshot.state(p)
                if key(v)in VOIDS or p in snapshot.protected:raise UserError('Retain literal real garland endpoint '+str(p))
                supports[p]=v
            for i,p in enumerate(points):
                add(p,'minecraft:flowering_azalea_leaves'if i%3==1 else'minecraft:oak_leaves',label,
                    distance=7,persistent=True,waterlogged=False)
        # The native leaf algorithm is the same for flowering azalea and the
        # other vanilla leaves. Preserve their actual material IDs in the plan.
        modeled={p:('minecraft:azalea_leaves'if key(v)=='minecraft:flowering_azalea_leaves'else v)for p,v in delta.items()}
        for p,d in leaf_distances(modeled,snapshot.state).items():
            delta[p]=state(registry,key(delta[p]),distance=d,persistent=True,waterlogged=False)
            for vector in(*FACES.values(),(0,1,0),(0,-1,0)):
                q=plus(p,vector)
                if q not in delta:before[q]=snapshot.state(q)
        # An honest actual three-wide central alley and little court connector,
        # not a proposed universal widening or a new route through old objects.
        columns={(x,z)for x in(1031,1032,1033)for z in range(-1269,-1257)}
        columns|={(x,z)for x in(1036,1037,1038)for z in range(-1274,-1271)}
        columns|={(1036,z)for z in range(-1272,-1269)}|{(x,-1270)for x in range(1031,1037)}
        for x,z in columns:
            for y in(63,64,65):
                p=(x,y,z);v=snapshot.state(p);routes[p]=v
                if y>63 and key(v)not in VOIDS:raise UserError('Source cannot claim an obstructed clear route '+str((p,v)))
                if y==63 and key(v)in VOIDS|{'minecraft:water'}:raise UserError('Actual walking support required')
        if set(delta)&(set(routes)|windows):raise UserError('A planter or garland blocks an actual window/view/walking body')
        if len(delta)!=17:raise UserError('Keep the exact small photo-led pocket')
        rule=require_outdoor_rule(delta,'Photo-led flowering clay urns and three connected leaf swags')
        before.update(supports);before.update(routes);sources=snapshot.sources.copy()
    finally:snapshot.close()
    canonical=read_json(home/'dashboard/settlement/backup-receipt.json')
    docs={}
    for name,blocks,verify in(('before-VERIFY-ONLY.json',before,True),('greenery-DELTA-PROPOSAL.json',delta,False),
            ('after-VERIFY-ONLY.json',before|delta,True),('normal-joins-SETTLE-ONLY.json',delta,True)):
        doc=payload(registry,canonical['sha256'],blocks,'One actual-photo-led fuller western alley pocket: '+name,before=verify,
            priority={p:0 if key(v).endswith('flower_pot') else 1 for p,v in delta.items()})
        doc.update(construction_forbidden=True,native_before_and_master_admission_required=True,
            source_observed_checkpoint_id=CHECKPOINT[0],source_observed_checkpoint_sha256=CHECKPOINT[1])
        docs[name]=doc
    manifest={'format':'awft-photo-led-west-alley-greenery:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'actual_reference_photo_sha256':PHOTO_SHA,'observed_checkpoint_id':CHECKPOINT[0],'observed_checkpoint_sha256':CHECKPOINT[1],
        'targets':len(delta),'new_clay_urns':2,'new_leaf_fills_and_garlands':15,'block_entities_or_inventory_tags':0,
        'held_existing_details':[[1033,69,-1260],[1032,69,-1261]],'retained_window_view_cells':len(windows),
        'literal_route_columns':len(columns),'retained_supports':[{'position':p,'state':v}for p,v in supports.items()],
        'roles':[{'position':p,'role':roles[p]}for p in delta],'rule':rule,'saved_sources':sources,'custody':custody,
        'camera_suggestions':[{'feet':[1032.5,64,-1258.5],'look':[1032,67,-1269]},
                              {'feet':[1038.5,64,-1274.5],'look':[1031,67,-1268]}],
        'boundaries':'No original structural/window/sign/inventory/plant cell changes, no lower alley clutter, no new trees. Actual model joins, survival and day/night photo acceptance remain future Native/art gates.',
        'reserve_guard':reserve,'native_actions':0,'world_writes':0,'artistic_acceptance':False}
    raw={n:(json.dumps(d,separators=(',',':'))+'\n').encode()for n,d in docs.items()}
    manifest['files']={n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in raw.items()}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>2*1024**2:raise UserError('Finite2MiB pocket output exceeded')
    out=home/'staging'/('west-photo-led-greenery-'+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return{'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'targets':len(delta),'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
