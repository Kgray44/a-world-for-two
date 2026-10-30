"""Bounded saved player-link and initialized-toolbox custody, never live files."""
from __future__ import annotations
import argparse,hashlib,io,json,time,zlib
from pathlib import Path
import nbtlib
from control_room.common import UserError,digest,read_json
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_urban_custody import canonical
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_north_rebuild_custody import decoded_chunk
from tools.artistic_zipline_catenary import reader_budget
from tools.native_eastern_relocation import SEALED_CATALOG_SHA
from tools.native_eastern_relocation_current import CATALOG
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB=1024**2
TOOLBOX='compass-bend/shared-repair-court:room:0'

def read_player(raw):
    if len(raw)>MIB:raise UserError('Bounded compressed current player member required')
    de=zlib.decompressobj(16+zlib.MAX_WBITS);plain=de.decompress(raw,4*MIB+1)
    if len(plain)>4*MIB or not de.eof or de.unused_data or de.unconsumed_tail:raise UserError('Complete bounded current player gzip required')
    stream=io.BytesIO(plain);doc=nbtlib.File.parse(stream)
    if stream.read(1):raise UserError('Trailing current player NBT')
    return doc

def links(doc):
    seen=[0];found=[]
    def walk(value,depth=0):
        seen[0]+=1
        if seen[0]>300000 or depth>64:raise UserError('Bounded complete player tree')
        if isinstance(value,nbtlib.Compound):
            for key,child in value.items():
                if key=='CreateToolboxData':
                    if not isinstance(child,nbtlib.Compound):raise UserError('Unknown native toolbox table type')
                    for slot,entry in child.items():
                        if not isinstance(entry,nbtlib.Compound) or 'Pos' not in entry:raise UserError('Unknown native toolbox link shape')
                        p=entry['Pos']
                        if isinstance(p,nbtlib.IntArray) and len(p)==3:point=tuple(map(int,p))
                        elif isinstance(p,nbtlib.Compound) and all(k in p for k in ('X','Y','Z')):point=tuple(int(p[k]) for k in ('X','Y','Z'))
                        else:raise UserError('Unknown exact pinned native toolbox Pos shape')
                        found.append(point)
                walk(child,depth+1)
        elif isinstance(value,nbtlib.List):
            for child in value:walk(child,depth+1)
    walk(doc);return found

def prepare(home):
    home=Path(home).resolve();reserve=guard(MIB,MIB);reader_budget();receipt=read_json(home/'dashboard/settlement/backup-receipt.json');registry=read_json(home/'dashboard/settlement/registry.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    cat=checked(home/CATALOG,SEALED_CATALOG_SHA,2*MIB);row=next(r for r in cat['capsules'] if r['id']==TOOLBOX)
    src=checked(home/row['source_original']['path'],row['source_original']['sha256'],MIB)
    original=[(tuple(v['pos']),nbtlib.parse_nbt(v['nbt'])) for v in src['block_entities'] if str(nbtlib.parse_nbt(v['nbt'])['id'])=='create:toolbox']
    if len(original)!=1:raise UserError('One exact original toolbox required')
    pos,tag=original[0];snapshot=None;profiles=[];human_bed_references=0
    try:
        snapshot=BackupWorld(home,receipt,registry);snapshot.state(pos);doc=decoded_chunk(snapshot.regions[pos[0]//512,pos[2]//512],pos[0]//16,pos[2]//16)
        tags=[v for v in doc.get('block_entities',[]) if tuple(int(v[k]) for k in ('x','y','z'))==pos]
        if len(tags)!=1 or tags[0]!=tag:raise UserError('Current actual initialized full typed toolbox differs')
        if not isinstance(tag.get('UniqueId'),nbtlib.IntArray) or len(tag['UniqueId'])!=4:raise UserError('Already-initialized native UUID required; save must not generate one')
        inventory=tag.get('Inventory');compartments=inventory.get('Compartments') if isinstance(inventory,nbtlib.Compound) else None
        if not isinstance(compartments,nbtlib.List) or len(compartments)!=8:raise UserError('Exact eight saved filter compartments; no native filter normalization')
        members=[(name,m) for name,m in snapshot.files.items() if '/playerdata/' in name and name.endswith('.dat')]
        if not 1<=len(members)<=16:raise UserError('Complete nonempty current saved profile set bounded16')
        for name,meta in sorted(members):
            raw=snapshot.archive.read(name)
            if len(raw)!=meta['size'] or digest_bytes(raw)!=meta['sha256']:raise UserError('Actual current player member changed')
            player=read_player(raw);points=links(player)
            if pos in points:raise UserError('Real saved player link targets the toolbox; normal unlink workflow required')
            if all(k in player for k in ('SpawnX','SpawnY','SpawnZ')) and (int(player['SpawnX']),int(player['SpawnY']),int(player['SpawnZ'])) in ((1296,65,-1250),(1296,65,-1249)):human_bed_references+=1
            profiles.append({'file_name':Path(name).name,'sha256':meta['sha256'],'bytes':meta['size'],'matching_toolbox_links':0})
    finally:
        if snapshot:snapshot.close()
    out=home/'staging'/('toolbox-full-saved-link-authority-'+str(time.time_ns()));out.mkdir();p=out/'saved-custody-PRIVATE.json'
    record={'format':'awft-toolbox-saved-player-custody:1','checkpoint_id':receipt['id'],'checkpoint_sha256':receipt['sha256'],'toolbox_source_position':list(pos),
        'source_catalog_sha256':SEALED_CATALOG_SHA,'actual_full_typed_source_unchanged':True,'native_initialized_UUID_already_saved':True,'eight_native_saved_filters':True,
        'current_player_profiles':profiles,'matching_saved_links':0,'actual_blue_bed_respawn_references':human_bed_references,
        'native_handler_links_and_slots_observed':False,'native_actions':0,'source_sha256':digest(Path(__file__)),'reserve_guard':reserve}
    p.write_bytes(canonical(record)+b'\n');return {'folder':str(out),'sha256':digest(p),'profiles':len(profiles),'matching_links':0,'human_bluebed_respawn_references':human_bed_references,'native_actions':0}

def digest_bytes(raw):return hashlib.sha256(raw).hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
