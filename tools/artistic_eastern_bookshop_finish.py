"""Photo-led Worn Book reading/binding interior, new AIR cells only.

The genuine Native-passed room/stock stays literal. This finite first scene is
separate from paired-entry repair and from any future contextual room scenes.
"""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools import artistic_eastern_compound_sprint as e
from tools.artistic_eastern_entry_repair import actual_sources,checked
from tools.artistic_materials import require_material_rule
from tools.artistic_north_bank_east import native_payload
from tools.playtest import guard

MIB=1024**2
ENTRY=('staging/eastern-current14-entry-repair-1793237214610305800/manifest.json',
       '66faec7eafae57bf7a6e0e0dc8cf4c03f2e68d36e7cc34a983bc8a4d7c22ffa5')


def design(registry,base,source):
    delta={};roles=[];mounts=[];origin=source['origin'];body=set()
    for route in source['routes']:
        for q in route.get('feet_local',[]):
            x,y,z=(q[k]+origin[k]for k in range(3));body.update(((x,y,z),(x,y+1,z)))
    for route in source['geometry_proof'].get('vertical_routes',[]):
        for x,y,z in route.get('blocks',[]):
            for h in(1,2):body.add((x+origin[0],y+h+origin[1],z+origin[2]))
    # Real three-wide longitudinal/cross aisles plus the existing west entry
    # approach. No furniture maze; the physical one-block door is a threshold.
    aisle={(x,z)for x in range(1255,1258)for z in range(-1215,-1202)}
    aisle|={(x,z)for x in range(1252,1260)for z in range(-1211,-1208)}
    aisle|={(x,z)for x in range(1251,1254)for z in range(-1209,-1202)}
    aisle_body={(x,y,z)for x,z in aisle for y in(65,66)}
    if any(base.get(q)!='minecraft:air'for q in aisle_body):raise UserError('A literal proposed three-wide reading-room aisle is not actually clear in the verified field')
    body|=aisle_body

    def put(q,name,role,*,mount=None,**props):
        if q in body:raise UserError('A new reading-room object would obstruct preserved circulation: '+str(q))
        if base.get(q)!='minecraft:air':raise UserError('AIR-only finishing cannot replace any existing state or unknown point: '+str((q,base.get(q))))
        if q in delta:raise UserError('Every authored finishing cell has one unambiguous purpose')
        delta[q]=e.state(registry,name,**props);roles.append({'position':list(q),'state':delta[q],'purpose':role})
        if mount:mounts.append((q,mount))

    # A substantial actual book wall, its taller middle beneath the clear
    # ceiling. These are bookshelves, not copied inventories or false rooms.
    for z in range(-1215,-1210):
        put((1260,65,z),'chipped:historical_oak_bookshelf','lower nautical-history and sea-journal shelves',mount=(1260,64,z))
        put((1260,66,z),'chipped:oak_lighted_bookshelf','upper illuminated maritime volumes in the real book wall',mount=(1260,65,z))
    for y in(65,66):put((1254,y,-1218),'chipped:dusty_bookshelf','compact incoming book stock beside the existing receiving barrel',mount=(1254,y-1,-1218))
    put((1260,65,-1218),'chipped:oak_bookshelf','low returning-books endcap with a contained flower',mount=(1260,64,-1218))
    put((1260,66,-1218),'fishofthieves:potted_white_plumeria','contained soft-white flower on the full bookshelf endcap',mount=(1260,65,-1218))
    put((1259,65,-1218),'chipped:mixed_oak_bookshelf','solid low navigation-reference counter',mount=(1259,64,-1218))
    put((1259,66,-1218),'supplementaries:globe','real rotatable globe for the shop nautical-reference corner',mount=(1259,65,-1218),facing='south',powered=False,rotation=0,waterlogged=False)

    # Binding/repair workbench beside the retained lectern and map table.
    put((1253,65,-1213),'handcrafted:dark_oak_desk','bookbinder repair and order desk',mount=(1253,64,-1213),facing='west',color='brown',waterlogged=False)
    put((1253,66,-1213),'handcrafted:stackable_book','bindings awaiting repair, real ordinary book models',mount=(1253,65,-1213),facing='west',books=4,seed=37)
    put((1254,65,-1213),'handcrafted:dark_oak_chair','bookbinder seat facing the actual repair desk',mount=(1254,64,-1213),facing='west',color='brown',waterlogged=False)
    put((1253,65,-1212),'handcrafted:dark_oak_side_table','small adjacent task-lamp stand',mount=(1253,64,-1212),facing='west',color='none',waterlogged=False)
    put((1253,66,-1212),'mcwlights:golden_low_candle_holder','warm small practical binding-desk light',mount=(1253,65,-1212),lit=True)
    put((1253,65,-1214),'supplementaries:book_pile','low real book bundle beside the repair desk',mount=(1253,64,-1214),books=4,waterlogged=False)

    # One public browsing table beside the book wall, separate from the
    # more relaxed south-window reading nook; both leave the wide spine clear.
    for x,z in((1258,-1215),(1259,-1215),(1258,-1213),(1259,-1213)):
        put((x,65,z),'minecraft:brown_carpet','small muted browsing rug edge',mount=(x,64,z))
    put((1259,65,-1214),'handcrafted:dark_oak_table','new-arrivals browsing table beside the reference shelves',mount=(1259,64,-1214),shape='single',color='none',waterlogged=False)
    put((1259,66,-1214),'handcrafted:stackable_book','new maritime titles displayed on the real table',mount=(1259,65,-1214),facing='west',books=3,seed=16)
    put((1258,65,-1214),'handcrafted:dark_oak_bench','small browsing perch outside the central aisle',mount=(1258,64,-1214),facing='east',shape='single',color='brown',waterlogged=False)
    for x in range(1258,1261):
        for z in(-1205,-1203):put((x,65,z),'minecraft:brown_carpet','two edges of the intimate south-window reading rug',mount=(x,64,z))
    put((1259,65,-1204),'handcrafted:dark_oak_table','quiet two-reader window table',mount=(1259,64,-1204),shape='single',color='none',waterlogged=False)
    put((1259,66,-1204),'handcrafted:stackable_book','shared open-reading book models',mount=(1259,65,-1204),facing='south',books=2,seed=24)
    for x,face in((1258,'east'),(1260,'west')):
        put((x,65,-1204),'handcrafted:dark_oak_chair','paired quiet reading seat at the window table',mount=(x,64,-1204),facing=face,color='brown',waterlogged=False)
    put((1260,65,-1202),'chipped:botanical_oak_bookshelf','low full-block reading-nook plant stand',mount=(1260,64,-1202))
    put((1260,66,-1202),'regions_unexplored:potted_blue_lupine','contained blue coastal reading-nook flower',mount=(1260,65,-1202))

    put((1260,66,-1207),'handcrafted:dark_oak_shelf','small actual backed overflow-book display',mount=(1261,66,-1207),facing='west',shape='single',type=3)
    put((1260,67,-1207),'handcrafted:stackable_book','small overflow shelf volumes below the ceiling',mount=(1260,66,-1207),facing='west',books=3,seed=52)
    for q,back,face in(((1260,67,-1214),(1261,67,-1214),'west'),((1260,67,-1208),(1261,67,-1208),'west'),((1256,67,-1218),(1256,67,-1219),'south'),((1258,67,-1202),(1258,67,-1201),'north')):
        put(q,'mcwlights:tavern_wall_lantern','small supported warm bookshop/task wall light above walking headroom',mount=back,facing=face)
    post=base|delta
    for q,back in mounts:
        if back not in post or e.key(post[back])in e.VOID or e.key(post[back])in('minecraft:water','minecraft:lava')or e.key(post[back]).startswith(('mcwwindows:','mcwdoors:')):
            raise UserError('A real shelf, prop, lamp or furniture lacks its intended existing/new mount: '+str((q,back)))
    if any(post.get(q)!='minecraft:air'for q in body):raise UserError('Finishing altered a preserved actual circulation/body point')
    owned={tuple(v[:3])for v in source['complete_expected_state_context_ONLY']}
    whole={q:v for q,v in post.items()if q in owned or q in delta}
    return delta,roles,mounts,sorted(aisle),require_material_rule(whole,'Worn Book full compound with bookshop finish')


def prepare(home):
    home=Path(home).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()):raise UserError('Private artistic Source output only')
    reserve=guard(4*MIB,16*MIB);reg=read_json(home/'dashboard/settlement/registry.json');receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    actual=actual_sources(home);current={}
    for _,_,field,_ in actual:current.update(field)
    ident,source,own,ref=next(r for r in actual if r[0]=='worn-book')
    ep=home/ENTRY[0];entry=checked(ep,ENTRY[1]);dr=entry['files']['entry-and-low-fitting-DELTA'];entry_delta=e.checked(home,(dr['path'],dr['sha256']))
    from tools.artistic_bridge_refinement import flatten
    changes=flatten(entry_delta);base=current|changes
    delta,roles,mounts,aisle,material=design(reg,base,source)
    # Exact main ground-floor room, including its unchanged floor, existing
    # furnishings, ceiling and genuine repaired entrance; other future wings
    # never become readonly AIR acceptance context for this finishing pass.
    scope={(x,y,z)for x in range(1250,1262)for y in range(64,69)for z in range(-1219,-1200)}
    if not scope<=set(base):raise UserError('Complete verified main-room field required')
    supports={q:base[q]for _,q in mounts if q not in delta};after={q:base[q]for q in scope}|delta
    out=home/'staging'/('worn-book-photo-finish-'+str(time.time_ns()));out.mkdir();files={}
    for name,field in [('AIR-targets-BEFORE',{q:current[q]for q in delta}),('retained-mounts-BEFORE',supports),('bookshop-AIR-only-DELTA',delta),('bookshop-normal-settle',delta),('complete-main-room-AFTER',after)]:
        doc=native_payload(reg,field,receipt['sha256'],'SOURCE ONLY Worn Book photo-led reading/binding scene — '+name);doc.update(construction_forbidden=True,verification_only=True,block_entities=[],commands=[])
        p=out/(name+'.json');p.open('x',encoding='utf8').write(json.dumps(doc,separators=(',',':'))+'\n');files[name]={'path':p.relative_to(home).as_posix(),'sha256':digest(p),'bytes':p.stat().st_size}
    manifest={'format':'awft-worn-book-photo-led-finish-SOURCE:1','files':files,'actual_original_full_proof':ref,'entry_repair_prerequisite':{'path':ENTRY[0],'sha256':ENTRY[1],'delta_sha256':dr['sha256']},
      'literal_three_wide_aisle_columns':[[x,z]for x,z in aisle],'purposeful_new_objects':roles,'support_edges':[{'new':list(q),'mount':list(b)}for q,b in mounts],
      'complete_building_material_rule':material,'counts':{'new_cells':len(delta),'complete_ground_room_cells':len(after),'three_wide_aisle_columns':len(aisle),'retained_native_states_overwritten':0,'new_tags_or_copied_inventory':0},
      'source_sha256':digest(Path(__file__)),'photo_refs':['logs/visual-review/east63-1793235690/worn-book-interior.png'],
      'after_view':{'feet':[1256.5,65,-1209.5],'look_at':[1259.5,66,-1213.5]},'native_actions':0,'world_writes':0,'construction_forbidden':True,'reserve_guard':reserve,
      'required_next_gates':['Fresh empty-world native AIR targets/mounts before','Actual entry repair completed first; no window-door metadata acceptance','Root admit exact AIR-only delta with no NBT/inventory load','Normal native settle/strict room after and real furnished scene walk/model/light/art review']}
    p=out/'manifest.json';p.open('x',encoding='utf8').write(json.dumps(manifest,indent=2)+'\n')
    if sum(p.stat().st_size for p in out.iterdir())>16*MIB:raise UserError('Finite16MiB finishing output exceeded')
    return {'folder':str(out),'manifest_sha256':digest(p),'counts':manifest['counts'],'files':files,'world_writes':0,'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);v=a.parse_args();print(json.dumps(prepare(v.home),indent=2))
