"""Separate W3 porch feet and real-door corrections; never edit frozen48.

The original strict equality proof remains true. These small source semantics
defects need separate actual AIR preimages and a full corrected composite.
"""
from __future__ import annotations
import argparse
import hashlib,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_west_r2_frontage import construct as base_construct,LABELS,key
from tools.artistic_west_r2_refine import construct as photo_construct,check as photo_check,BASE
from tools.artistic_bridge_refinement import flatten
from tools.artistic_spawn_plaza import state
from tools.artistic_north_bank_east import NorthTerrain,native_payload
from tools.artistic_west_r2_study import ZIP
from tools.playtest import guard
from tools.artistic_zipline_catenary import reader_budget

MIB=1024**2
PHOTO=('staging/west3-photo-refine-1793173018733764300/full-after-VERIFY-ONLY.json','1a1b168063d20a4015b125a378fe50581b0afc59112353e2898dfb46d2101e53')


def corrections(registry):
    feet={(1076,64,-1262):state(registry,'minecraft:stone_bricks'),(1078,64,-1262):state(registry,'minecraft:stone_bricks')}
    doors={}
    for x,z,face in ((1077,-1263,'north'),(1081,-1262,'east')):
        for y,half in ((65,'lower'),(66,'upper')):
            doors[x,y,z]=state(registry,'mcwdoors:dark_oak_cottage_door',facing=face,half=half,hinge='left',open=False,powered=False)
    return feet,doors


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(2*MIB,8*MIB);memory=reader_budget()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private artistic correction only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or(receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha)or'stopped'not in receipt.get('scope','').lower():raise UserError('Exact current stopped checkpoint required')
    registry=read_json(home/'dashboard/settlement/registry.json')
    for rel,sha in (BASE,PHOTO,ZIP):
        if digest(home/rel)!=sha:raise UserError('Frozen W3/refinement/V2 source custody changed')
    original=read_json(home/BASE[0]);photo=read_json(home/PHOTO[0]);combined=flatten(photo);feet,doors=corrections(registry);changed={**feet,**doors}
    if any(flatten(original).get(q,'minecraft:air')!='minecraft:air'for q in changed):raise UserError('Only the six originally authored AIR positions may be corrected')
    if set(changed)&set(flatten(read_json(home/ZIP[0]))):raise UserError('Keep every placed zipline/flight cell')
    # Reuse COMPLETE original+photo material/route checks without modifying the
    # frozen photo artifact. Assign the small feet/doors to their true building.
    audit=photo_construct(registry,flatten(original))
    audit.blocks.update(changed)
    for q in feet:audit.owners[q]=LABELS[0]
    for q in doors:audit.owners[q]=LABELS[0]if q[0]==1077 else LABELS[1]
    checks=photo_check(audit);combined.update(changed)
    terrain=NorthTerrain(home,receipt,registry);before={};mounts={}
    try:
        for q in changed:
            actual=terrain.state(*q)
            if actual!='minecraft:air'or q in terrain.entities:raise UserError('Current exact AIR and no BE required; preserve any later user work: '+str(q))
            before[q]=actual
        for q in (*feet,(1077,65,-1263),(1081,65,-1262)):
            lower=(q[0],q[1]-1,q[2]);s=terrain.state(*lower)
            if s is None or key(s)in('minecraft:air','minecraft:water','minecraft:cave_air','minecraft:void_air')or lower in terrain.entities:raise UserError('Actual retained stone/wood mounting floor required')
            mounts[lower]=s
        sources=terrain.snapshot.sources
    finally:terrain.close()
    docs={
      'porch-feet2-PROPOSAL.json':native_payload(registry,feet,checkpoint_sha,'W3 ADDITIVE2 — real stone porch feet, separate from frozen48'),
      'porch-feet2-before-VERIFY-ONLY.json':native_payload(registry,{q:before[q]for q in feet},checkpoint_sha,'VERIFY ONLY — exact AIR before two porch feet'),
      'doors4-PROPOSAL.json':native_payload(registry,doors,checkpoint_sha,'W3 SEPARATE4 — real normal Wick/Cooper door halves; no existing inventory'),
      'doors4-before-VERIFY-ONLY.json':native_payload(registry,{q:before[q]for q in doors},checkpoint_sha,'VERIFY ONLY — exact AIR before the four real door halves'),
      'retained-mounts-VERIFY-ONLY.json':native_payload(registry,mounts,checkpoint_sha,'VERIFY ONLY — actual retained masonry/wood below feet and doors'),
      'full-photo-plus-feet2-VERIFY-ONLY.json':native_payload(registry,{**flatten(photo),**feet},checkpoint_sha,'VERIFY ONLY — full W3 plus frozen48 and two supported feet',tags={tuple(r['pos']):r['nbt']for r in original['block_entities']}),
      'full-photo-plus-feet-and-doors-VERIFY-ONLY.json':native_payload(registry,combined,checkpoint_sha,'VERIFY ONLY — full W3 plus frozen48,2feet,4real door halves',tags={tuple(r['pos']):r['nbt']for r in original['block_entities']}),
      'normal-joins6-SETTLE-ONLY.json':native_payload(registry,changed,checkpoint_sha,'NORMAL JOIN ONLY — exact6 supplemental entry/support cells; no replay')}
    for name,doc in docs.items():
        if not name.endswith('-PROPOSAL.json'):doc.update(construction_forbidden=True,verification_only=True)
    raw={n:(json.dumps(d,separators=(',',':'))+'\n').encode()for n,d in docs.items()}
    manifest={'format':'awft-w3-separate-entry-support-corrections:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
      'frozen48_unchanged':PHOTO,'prior_W3_unchanged':BASE,'feet2':[list(q)for q in feet],'doors4':[list(q)for q in doors],
      'reason':'Actual source circulation erased two declared doors; porch posts also need real base feet. Prior strict source equality was not a walkability/architectural support certification.',
      'checks':checks,'saved_sources':sources,'reserve_guard':reserve,'reader_budget':memory,'current_BE_or_inventory_targets':0,
      'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}for n,b in raw.items()},'native_actions':0,'world_writes':0,
      'next_gate':'Parent exact native AIR/mount preflight; apply the two separate small corrections only after review, normal joins and full composite strict/native photos. Never replay frozen48 or an old source over later progress.'}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>8*MIB:raise UserError('Finite entry correction output cap exceeded')
    out=home/'staging'/('west3-separate-entry-support-fix-'+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True);args=a.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
