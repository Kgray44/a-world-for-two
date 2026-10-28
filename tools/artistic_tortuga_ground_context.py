"""Additive ground/trade-pair context; frozen original868 stays unchanged."""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import native_payload
from tools.artistic_west_coverage import actual_geometry
from tools.playtest import guard

MIB=1024**2
FOLDER='staging/tortuga-west-ground-1793196333621516200'
PINS={'manifest.json':'8fc3742481193d448fe54fc1886a466358c7dcd39a028e5994d3258ef649eb45',
      'west-ground-workspaces-PROPOSAL.json':'16b3fdd20cda48c1251c00adbe3cc2608ccd3f14def8c7209dd0d77f0f6611ac',
      'full-after-and-walkclearance-VERIFY-ONLY.json':'6641639a895a30e86e068b5a4171093adc90517aad92ffcc109e2086556f1274'}
PAIR_MANIFEST='staging/tortuga-trade-pair-1793195118561023300/manifest.json'


def prepare(home):
    home=Path(home).resolve();reserve=guard(2*MIB,8*MIB)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private source-only context')
    for filename,sha in PINS.items():
        if digest(home/FOLDER/filename)!=sha:raise UserError('Frozen868 original changed')
    manifest=read_json(home/FOLDER/'manifest.json');pair={};tags={}
    for name in('crooked-iron','sounding-line'):
        pair.update(actual_geometry(home,PAIR_MANIFEST,name+'-PROPOSAL.json'))
        for row in read_json(home/Path(PAIR_MANIFEST).parent/(name+'-PROPOSAL.json')).get('block_entities',[]):tags[tuple(row['pos'])]=row['nbt']
    placement=flatten(read_json(home/FOLDER/'west-ground-workspaces-PROPOSAL.json'))
    conflicts=[(q,s,pair[q])for q,s in placement.items()if q in pair and s!=pair[q]]
    if conflicts:raise UserError('Do not change either source: actual geometry conflict '+str(conflicts[:5]))
    ground=read_json(home/FOLDER/'full-after-and-walkclearance-VERIFY-ONLY.json');field=flatten(ground)
    for row in ground.get('block_entities',[]):tags[tuple(row['pos'])]=row['nbt']
    columns={tuple(q)for route in manifest['routes']for q in route['cells_xz']}
    walking={(x,y,z):'minecraft:air'for x,z in columns for y in(64,65)}
    if any(pair.get(q,'minecraft:air')!='minecraft:air'for q in walking):raise UserError('Actual pair obstructs genuine two-high human walking')
    overhangs={q:s for q,s in pair.items()if(q[0],q[2])in columns and q[1]==66 and s!='minecraft:air'}
    after={**field,**pair}
    registry=read_json(home/'dashboard/settlement/registry.json');backup=manifest['checkpoint_sha256']
    files={'retained-two-high-walking-VERIFY-ONLY.json':native_payload(registry,walking,backup,'VERIFY ONLY — two-wide ground paths remain two-high after real trade-pair fixtures'),
           'future-pair-plus-ground-VERIFY-ONLY.json':native_payload(registry,after,backup,'VERIFY ONLY — exact frozen West ground plus real future trade-pair geometry',tags=tags)}
    raw={}
    for name,doc in files.items():
        doc.update(construction_forbidden=True,verification_only=True)
        raw[name]=(json.dumps(doc,separators=(',',':'))+'\n').encode()
    note={'format':'awft-west-ground-additive-context:1','checkpoint_id':manifest['checkpoint_id'],'checkpoint_sha256':backup,'source_sha256':digest(Path(__file__)),
          'unchanged868_placement_sha256':PINS['west-ground-workspaces-PROPOSAL.json'],'frozen_originals_modified':False,
          'scope':'Original current-after three-high AIR is valid before pair construction only; this companion preserves literal future Y66 fixtures and two-high actor clearance',
          'actual_future_overhangs_at_Y66':[{'position':list(q),'state':s}for q,s in sorted(overhangs.items())],
          'not_a_native_collision_or_model_overhang_acceptance':True,'future_pair_native_placement_then_normal_joins_and_full_context_required':True,
          'native_actions':0,'world_writes':0,'reserve_guard':reserve,'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in raw.items()}}
    raw['manifest.json']=(json.dumps(note,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>8*MIB:raise UserError('Finite8MiB source-context output cap')
    out=home/'staging'/('tortuga-west-ground-context-'+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'overhangs':len(overhangs),'files':note['files'],'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);args=a.parse_args();print(json.dumps(prepare(args.home),indent=2))
