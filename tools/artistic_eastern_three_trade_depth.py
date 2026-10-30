"""A richer combined SOURCE revision of the unplaced three-scene80 packet.

The original packet remains immutable. This is an alternative first placement,
not an overlay to replay after80 was placed. No live API/save/NBT is touched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from control_room.common import UserError, digest, read_json
from tools import artistic_eastern_first_three_detail as original
from tools.artistic_bridge_refinement import flatten
from tools.artistic_city_planning_map import EAST, read as frozen_layout
from tools.artistic_create_substrate import verify_zinc_factory
from tools.artistic_ground_stability import natural_mount
from tools.artistic_materials import require_outdoor_rule
from tools.artistic_north_bank_east import NorthTerrain, native_payload, GROUND, SOFT, NORTH_SOFT
from tools.artistic_spawn_plaza import state
from tools.artistic_tortuga_frontages import AIR, POTS, key
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB = 1024**2
BASE = ('staging/eastern-three-trade-greens-1793229352277411400/manifest.json',
        '71e45c31adaa030fd42815cee98c636b0f76b9af4b983075d772e61dac0b7480')
LIMIT = 130
VIEWS = (
    {'name':'Coal repair alcove','feet':[1357.5,64,-1161.5],'look':[1359.5,65.5,-1162]},
    {'name':'Shoal chart canopy','feet':[1357.5,64,-1184.5],'look':[1355.5,65.5,-1186]},
    {'name':'Thin Sail mending edge','feet':[1377.5,64,-1126.5],'look':[1379,65.5,-1125]},
)


def additions(registry):
    """Individually composed mounted details; no fresh container or fake goods."""
    cells, mounts, roots, objects = {}, {}, set(), []

    def put(q,name,role,*,mount=None,**props):
        if q in cells:
            raise UserError('Unique small detail cell required')
        cells[q]=state(registry,name,**props)
        objects.append({'position':list(q),'block':name,'role':role})
        if mount is not None:
            mounts[q]=mount

    # New restrained knee/cap/potted crown reaches one voxel off the post,
    # rather than adding another broad canopy or repainting the native wall.
    put((1361,66,-1161),'mythrais:curved_corbel_dark_oak','carved outward knee on the independent Coal timber',mount=(1360,66,-1161),facing='east',shape=0)
    put((1361,67,-1161),'minecraft:dark_oak_wood','one-block framed flower ledge above the carved knee',mount=(1361,66,-1161),axis='x')
    put((1360,68,-1161),POTS[4],'contained red fern on the full founded post cap',mount=(1360,67,-1161))
    put((1361,68,-1161),POTS[1],'contained plumeria on the little supported ledge',mount=(1361,67,-1161))
    put((1358,63,-1164),'minecraft:anvil','actual usable repair anvil following the lower natural shore ledge; no raised fill',facing='west')

    # An explicit side-mounted trade shelf and tableware give the pilot stall
    # a useful visible back/side face. These are native decor blocks, not Item
    # or inventory NBT inserted into somebody's existing container.
    put((1355,65,-1184),'handcrafted:dark_oak_shelf','supported little chart-stall side shelf',mount=(1355,65,-1185),facing='south',shape='single',type=3)
    put((1355,66,-1184),'handcrafted:wood_cup','pilot waiting mugs on the real wall shelf',mount=(1355,65,-1184),facing='south',pieces=3,waterlogged=False)
    put((1355,67,-1184),'minecraft:dark_oak_trapdoor','small vertical scalloped canopy end-board',mount=(1355,67,-1185),facing='south',half='top',open=True,powered=False,waterlogged=False)
    put((1356,67,-1184),'dawnoftimebuilder:charred_spruce_support_slab','thin modelled return to the shallow weathered canopy',mount=(1356,67,-1185),pillar_connection='nothing',waterlogged=False)

    # This bracket is above the complete two-high visiting body, not at the
    # shop doorway or across the lane. The real pot cannot grow a large tree.
    put((1378,66,-1123),'mythrais:curved_corbel_dark_oak','high carved mending-post knee above clear walking body',mount=(1379,66,-1123),facing='west',shape=0)
    put((1378,67,-1123),'minecraft:dark_oak_wood','short supported upper display ledge',mount=(1378,66,-1123),axis='x')
    put((1378,68,-1123),POTS[3],'contained tropical monstera on the high full ledge',mount=(1378,67,-1123))
    put((1379,66,-1125),'dawnoftimebuilder:charred_spruce_support_slab','shaped underside to the task-light arm',mount=(1379,67,-1125),pillar_connection='nothing',waterlogged=False)
    for x,z,plant in ((1379,-1130,'regions_unexplored:salmon_wisteria_shrub'),
                      (1379,-1122,'regions_unexplored:pink_lupine')):
        q=x,63,z
        put(q,'minecraft:dirt','tiny real soil pocket continuing the mender edge')
        roots.add(q)
        if plant.endswith('_shrub'):
            put((x,64,z),plant,'native rooted flowering shrub lower half',half='lower')
            put((x,65,z),plant,'native rooted flowering shrub upper half',half='upper')
        else:
            put((x,64,z),plant,'native rooted lupine beside the light post')
    # Only a one-person work alcove branches from the existing two-wide public
    # shoulder; it is not represented as a new two-wide city arterial.
    work_alcove={(1357,-1163)}
    return cells,mounts,roots,objects,work_alcove


def compose(registry,base,kept,main,walks):
    extra,mounts,roots,objects,alcove=additions(registry)
    if any(q in base or q in kept or(q[0],q[2])in main for q in extra):
        raise UserError('Additions must not replace80, native compound cells or any future main floor')
    full={**base,**extra}
    for x,z in walks|alcove:
        if any(full.get((x,y,z),AIR)!=AIR for y in(64,65)):
            raise UserError('Preserve the full public body and the explicit anvil access')
    for q,mount in mounts.items():
        if full.get(mount,AIR)==AIR:
            raise UserError('No floating display, knee, return, shelf or pot')
    if len(full)>LIMIT:
        raise UserError('Finite130 combined-target limit exceeded')
    require_outdoor_rule({q:s for q,s in full.items()if s!=AIR},'Three distinct mounted trade scenes, richer combined revision')
    return full,extra,mounts,roots,objects,alcove


def base_documents(home):
    path=home/BASE[0]
    if digest(path)!=BASE[1]:
        raise UserError('Keep the original80 packet immutable')
    manifest=read_json(path);docs={}
    for name,ref in manifest['files'].items():
        p=path.parent/name
        if digest(p)!=ref['sha256']:
            raise UserError('Original80 input bytes changed')
        docs[name]=read_json(p)
    return manifest,docs


def prepare(home):
    home=Path(home).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()):
        raise UserError('Owned private artistic staging only')
    reserve=guard(4*MIB,16*MIB)
    # A refusal exits before a saved-world object is created or any MCA read.
    budgets=[reader_budget()]
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified')is not True or(receipt.get('id'),receipt.get('sha256'))!=(original.CHECKPOINT,original.CHECKPOINT_SHA):
        raise UserError('Exact qualified6ad source required; later native freshness is a separate mandatory gate')
    registry=read_json(home/'dashboard/settlement/registry.json')
    bm,docs=base_documents(home)
    base=flatten(docs['detail-PLACE-ONCE.json']);kept,proofs=original.exact_sources(home)
    main={tuple(q)for b in frozen_layout(home,EAST)['buildings']for q in b['actual_building_floor_columns_xz']}
    walks=set(map(tuple,bm['two_wide_walking_columns_xz']))
    combined,extra,mounts,roots,objects,alcove=compose(registry,base,kept,main,walks)
    before=flatten(docs['before-VERIFY-ONLY.json']);supports=flatten(docs['stable-supports-VERIFY-ONLY.json']);after=flatten(docs['complete-after-VERIFY-ONLY.json'])
    tags={tuple(row['pos']):row['nbt']for row in docs['detail-PLACE-ONCE.json']['block_entities']}
    out=home/'staging'/('eastern-three-trade-depth-r2-'+str(time.time_ns()));out.mkdir()
    terrain=None
    try:
        terrain=NorthTerrain(home,receipt,registry)
        # New physical roots/anvil/operator floor need their own dry stable
        # stacks. Projected shelves/knees inherit an explicitly traced new80
        # timber support, rather than claiming the water under them is ground.
        zinc=verify_zinc_factory(home)
        for x,z in sorted({(x,z)for x,y,z in roots}|alcove|{(1358,-1164)}):
            mount=natural_mount(terrain.state,x,z,top=62 if (x,z)==(1358,-1164) else 63)
            last=mount.get('first_non_gravity')
            if not mount['stable']and last and last[3]=='create:zinc_ore':
                mount=dict(mount,stable=True,native_factory=zinc)
            if not mount['stable']:
                raise UserError('New alcove/planting refuses water, AIR or unstable gravity gaps: '+str((x,z,mount)))
            for xx,y,zz,s in mount['stack']:
                if(xx,y,zz)in terrain.entities:
                    raise UserError('No saved BE may become a new support')
                supports[xx,y,zz]=s
        for q in sorted(extra):
            s=terrain.state(*q)
            allowed=(GROUND|original.VOIDS|SOFT|NORTH_SOFT)if q in roots else(original.VOIDS|SOFT|NORTH_SOFT)
            if s is None or key(s)not in allowed or'waterlogged=true'in s or q in terrain.entities:
                raise UserError('New detail must preserve every saved/human object/BE/water: '+str((q,s)))
            before[q]=s
        for x,z in sorted(alcove):
            floor=terrain.state(x,63,z)
            if floor is None or key(floor)not in GROUND or(x,63,z)in terrain.entities:
                raise UserError('Anvil work alcove requires literal dry full flooring63')
            before[x,63,z]=floor;supports[x,63,z]=floor
            for y in(64,65):
                q=x,y,z;s=terrain.state(*q)
                if s is None or key(s)not in original.VOIDS|SOFT|NORTH_SOFT or'waterlogged=true'in s or q in terrain.entities or q in kept:
                    raise UserError('No widening work alcove through existing or human objects')
                before[q]=s;after[q]=AIR
                if key(s)not in original.VOIDS:
                    combined[q]=AIR
        budgets.append(reader_budget())
        sources=terrain.snapshot.sources;terrain.close();terrain=None
        after.update(supports);after.update(combined)
        output={
            'combined-PLACE-ONCE-NOT-AFTER80.json':native_payload(registry,combined,original.CHECKPOINT_SHA,'EAST3 R2 — alternative combined first placement; do not replay after80',tags=tags),
            'before-VERIFY-ONLY.json':native_payload(registry,before,original.CHECKPOINT_SHA,'VERIFY ONLY — exact original80 and new depth targets'),
            'stable-supports-VERIFY-ONLY.json':native_payload(registry,supports,original.CHECKPOINT_SHA,'VERIFY ONLY — actual dry native stacks and unchanged walking floors'),
            'complete-after-VERIFY-ONLY.json':native_payload(registry,after,original.CHECKPOINT_SHA,'VERIFY ONLY — existing compounds plus combined trade depth; no old NBT',tags=tags),
            'normal-survival-SETTLE-ONLY.json':native_payload(registry,{q:s for q,s in combined.items()if s!=AIR},original.CHECKPOINT_SHA,'NORMAL UPDATE ONLY — supported native combined new details'),
        }
        for name,doc in output.items():
            if not name.startswith('combined-PLACE'):
                doc.update(verification_only=True,construction_forbidden=True)
        raw={name:(json.dumps(doc,separators=(',',':'))+'\n').encode()for name,doc in output.items()}
        manifest={'format':'awft-eastern-three-trade-depth-r2:1','source_sha256':digest(Path(__file__)),'base_manifest':BASE,'base80_immutable':True,
          'source_checkpoint_id':original.CHECKPOINT,'source_checkpoint_sha256':original.CHECKPOINT_SHA,'actual_native55_proofs':proofs,
          'combined_targets':len(combined),'additional_detail_cells':len(extra),'new_extra_containers_or_BE_tags':0,'old_inventory_writes':0,'native_actions':0,'world_writes':0,
          'new_objects':objects,'new_roots':[list(q)for q in sorted(roots)],'new_support_links':[{'position':list(q),'support':list(m)}for q,m in sorted(mounts.items())],
          'retained_two_wide_visiting_columns':len(walks),'one_person_work_alcove_columns':[list(q)for q in sorted(alcove)],'views_SOURCE_ONLY':VIEWS,
          'saved_sources':sources,'reader_peak_RSS_bytes':max(r['owned_reader_rss_bytes']for r in budgets),'reserve_guard':reserve,
          'status':'SOURCE ONLY — all native admission, plant survival, model collision and rendered art checks pending',
          'required_native_gate':'Use either80 OR this combined revision while both remain unplaced. Fresh Root serialized BEFORE+supports must exactly match current world; any human/construction difference refuses. Never replay after80 or erase later edits.',
          'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}for n,b in raw.items()}}
        raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
        if sum(map(len,raw.values()))>16*MIB:
            raise UserError('Finite16MiB private packet limit exceeded')
        for n,b in raw.items():(out/n).open('xb').write(b)
        return{'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'combined_targets':len(combined),'additional':len(extra),'files':manifest['files']}
    except Exception as exc:
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps({'reason':type(exc).__name__+': '+str(exc),'source_sha256':digest(Path(__file__)),'world_writes':0})+'\n')
        raise UserError(str(exc)+'; retained '+str(out))from exc
    finally:
        if terrain is not None:terrain.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
