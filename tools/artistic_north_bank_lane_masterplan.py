"""Saved-only three-wide western public street binding; no world actions.

Castle owns detailed pavers/furniture. This supplies exact dry support/body
proof, respecting their five buildings and Grand's actual v2 reservation.
"""
from __future__ import annotations
from collections import Counter
import hashlib,heapq,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import NorthTerrain,AIR,SOFT,NORTH_SOFT
from tools.settlement_attractions import base
from tools.playtest import guard

MIB=1024**2;BOUNDS=(1008,-1280,1112,-1236)
WEST='staging/north-bank-west-five-final-20261028T0200Z'
WEST_SHA='7e8f392abbb71eec606cc7b2158a541d6689744cea22c125571a5214427c4254'
MASK_SHA='c5236daf51002d6297f72e56c3b49561f0ccb2b91de301b2c5a02d9d443be17a'
ZIP='staging/zipline-west-v2-source-1793152099836099800/all-v2-RESERVATION-ONLY.json'
ZIP_SHA='92ea594836795a61e00f5cc32290d49d1d47b9fd6eb55aeefc99d527acf8854d'
TERMINALS={'shipwright':(1019,-1269),'smith':(1046,-1257),'armoury':(1032,-1254),'tavern':(1061,-1259),'florist':(1086,-1252),'zipline-public-court':(1100,-1251)}
SPINE=((1032,-1269),(1032,-1257),(1054,-1257),(1072,-1256),(1086,-1253),(1100,-1251))

def path(adj,start,end,max_nodes=6000):
    if start not in adj or end not in adj:return None
    pending=[(abs(start[0]-end[0])+abs(start[1]-end[1]),0,start)];cost={start:0};prior={}
    while pending:
        _,g,q=heapq.heappop(pending)
        if g!=cost[q]:continue
        if q==end:
            result=[q]
            while q in prior:q=prior[q];result.append(q)
            return result[::-1]
        if len(cost)>max_nodes:raise UserError('Finite saved street search exhausted; no water/unknown fallback')
        for p in adj[q]:
            value=g+1
            if value<cost.get(p,10**9):cost[p]=value;prior[p]=q;heapq.heappush(pending,(value+abs(p[0]-end[0])+abs(p[1]-end[1]),value,p))
    return None

def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()):raise UserError('Private source masterplan only')
    reserve=guard(2*MIB,16*MIB);receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or receipt.get('id')!=checkpoint_id or receipt.get('sha256')!=checkpoint_sha:raise UserError('Exact current stopped source checkpoint required')
    folder=home/WEST;mask_path=folder/'future-solid-AIR-route-reservation-ONLY.json'
    if digest(folder/'manifest.json')!=WEST_SHA or digest(mask_path)!=MASK_SHA or digest(home/ZIP)!=ZIP_SHA:raise UserError('Exact final five shops and Grandv2 future masks required')
    future=flatten(read_json(mask_path));houses={(x,z) for x,y,z in future};zipwork=set(flatten(read_json(home/ZIP)))
    terrain=NorthTerrain(home,receipt,read_json(home/'dashboard/settlement/registry.json'));field={};blocked={};valid={};x0,z0,x1,z1=BOUNDS
    try:
        for cx in range((x0-1)//16,(x1+1)//16+1):
            for cz in range((z0-1)//16,(z1+1)//16+1):
                for x in range(max(x0-1,cx*16),min(x1+1,cx*16+15)+1):
                    for z in range(max(z0-1,cz*16),min(z1+1,cz*16+15)+1):
                        q=x,z;row=terrain.column(x,z);reason=None
                        if row['kind']!='dry':reason=row['kind']
                        elif q in houses:reason='future western shop/roof/AIR column'
                        else:
                            y=row['surface_y'];body=[terrain.state(x,y+dy,z) for dy in (1,2)]
                            if any(v is None or base(v) not in AIR|SOFT|NORTH_SOFT or 'waterlogged=true' in v for v in body):reason='actual body obstruction'
                            elif any((x,y+dy,z) in terrain.entities for dy in (0,1,2)):reason='saved BE'
                            elif any((x,y+dy,z) in zipwork for dy in (0,1,2)):reason='future Grandv2 frame/station/rider/work cell'
                            else:field[q]={'support':[x,y,z],'state':row['state'],'actual_body':body}
                        if reason:blocked[q]=reason
                terrain.check()
        for x in range(x0,x1+1):
            for z in range(z0,z1+1):
                cells=[(x+dx,z+dz) for dx in (-1,0,1) for dz in (-1,0,1)]
                if all(q in field for q in cells) and max(field[q]['support'][1] for q in cells)-min(field[q]['support'][1] for q in cells)<=1:valid[x,z]=cells
        adj={q:[p for p in ((q[0]-1,q[1]),(q[0]+1,q[1]),(q[0],q[1]-1),(q[0],q[1]+1)) if p in valid and abs(field[p]['support'][1]-field[q]['support'][1])<=1] for q in valid}
        routes=[];all_centers=set()
        for a,b in zip(SPINE,SPINE[1:]):
            nodes=path(adj,a,b)
            if nodes is None:raise UserError('Declared spine segment is not genuinely3wide/dry: '+str((a,b)))
            all_centers.update(nodes);routes.append({'id':'spine-'+str(len(routes)),'nodes_xz':[list(q) for q in nodes]})
        for name,q in TERMINALS.items():
            nodes=None
            for target in sorted(all_centers,key=lambda p:abs(p[0]-q[0])+abs(p[1]-q[1]))[:8]:
                nodes=path(adj,q,target)
                if nodes is not None:break
            if nodes is None:raise UserError('Exact outside threshold has no genuinely3wide route: '+name)
            all_centers.update(nodes);routes.append({'id':name,'nodes_xz':[list(p) for p in nodes],'threshold_note':'Stops outside the existing half-step; preserves qualified floor64 and exterior landing'})
        columns=set().union(*(set(valid[q]) for q in all_centers));witness=[field[q] for q in sorted(columns)];sources=terrain.snapshot.sources
    finally:terrain.close()
    data={'format':'awft-measured-west-public-lane:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
          'width':3,'routes':routes,'exact_support_body':witness,'columns':len(columns),'heights':dict(Counter(r['support'][1] for r in witness)),
          'future_west_mask_sha256':MASK_SHA,'Grand_v2_mask_sha256':ZIP_SHA,'sources':sources,'reserve':reserve,'world_actions':0,
          'status':'Saved support/body masterplan only; detailed pavers/furniture, fresh preimage, native walking and art remain pending',
          'limits':'No geometry placed; no whole-street raise/flattening; no house/zipline moved; reservation is never observedAIR'}
    raw=(json.dumps(data,indent=2)+'\n').encode()
    if len(raw)>16*MIB:raise UserError('Finite street proof output exceeded')
    output=home/'staging'/('north-bank-west-public-lane-'+str(time.time_ns()));output.mkdir();(output/'public-lane.json').write_bytes(raw)
    return {'folder':str(output),'sha256':hashlib.sha256(raw).hexdigest(),'routes':len(routes),'exact_3wide_columns':len(columns),'heights':data['heights'],'world_actions':0}
