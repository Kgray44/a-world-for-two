"""Prepare the owner's two exact requested originals for reserved dry plots.

No downloaded geometry is embedded in source control. Exact original downloads,
the pinned native flatten table and an authenticated saved checkpoint are inputs.
This writes NEW private proposals only; no game, placement or entity is started.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
import uuid

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_materials import require_material_rule
from tools.playtest import guard
from tools.settlement_attractions import AIR, BackupWorld, base, properties
from tools.structure_import import (LEGACY_DYES, contextual_legacy, litematic_geometry,
    read_source, rotate_position, rotate_record, state_string)

ORIGINALS = {
    'tavern': {'name': 'Pirate tavern', 'author': 'Evgesha765',
        'url': 'https://www.planetminecraft.com/project/pirate-tavern/',
        'file': 'pirate_tavern_evgesha7659618353.schematic',
        'sha256': 'e73346e4aa01bf9c0cea7a2e4e54b5d6b67f9f6c050b2460e6d9e6afa0301aeb',
        'bytes': 8911, 'size': (28, 42, 41), 'turns': 0,
        'origin': (1282, 60, -1337), 'bounds': (1282, -1337, 1309, -1297),
        'floor': 'Original lower hall floor4 -> world64; accommodationfloor12 -> world72; top101'},
    'shop': {'name': 'Fishermans shop', 'author': 'Shabani1 (source page; uploader bahs)',
        'url': 'https://market.phantom-node.com/post/fishermans-shop-m34wn72u',
        'file': 'fishermans-shop-m34wn72u.litematic',
        'sha256': '2a1ecefcdbba55f86480318107dfd396ba7c98d2731711e811b5cdd0e39b5309',
        'bytes': 4736, 'size': (34, 28, 21), 'turns': 1,
        'origin': (1314, 64, -1349), 'bounds': (1314, -1349, 1334, -1316),
        'floor': 'Original foundation0 -> world64; all positions rotated clockwise90 as one build'},
}
FLATTEN_SHA = '5d85b39417d6da62f804f6cc427cc42e8b4494fc12b11ad31b83f1276a6a1ca5'
MAX_OUTPUT = 16*1024**2
NATURAL = {'minecraft:'+n for n in ('grass_block','dirt','coarse_dirt','rooted_dirt','podzol','mud',
    'sand','gravel','stone','granite','diorite','andesite','clay','sandstone','moss_block')}
IMPORTED_TERRAIN = NATURAL | {'minecraft:'+n for n in ('air','cave_air','void_air','water','coal_ore',
    'iron_ore','short_grass','tall_grass','dandelion','poppy','azure_bluet','oxeye_daisy')}
VOID = {AIR, 'minecraft:cave_air', 'minecraft:void_air'}


def plant(key):
    return (key in {'minecraft:'+n for n in ('short_grass','tall_grass','fern','large_fern','dead_bush',
        'dandelion','poppy','azure_bluet','oxeye_daisy','cornflower','allium','pink_petals',
        'peony','rose_bush','lilac','sunflower','lily_of_the_valley','blue_orchid',
        'red_tulip','orange_tulip','white_tulip','pink_tulip')}
        or key == 'regions_unexplored:grass_sprouts' or key.startswith('farm_and_charm:wild_')
        or key in ('vinery:red_grape_bush','vinery:white_grape_bush'))


def ordinary_tree(key):
    # A plot permission is not authority to clear every modded wood structure.
    # The exact reserved shop survey also identified 47 natural willow logs
    # and 490 willow leaves. The retained court willow is outside this plot.
    return (bool(re.fullmatch(r'minecraft:(oak|spruce|birch|jungle|acacia|dark_oak|mangrove|cherry)_(log|leaves|wood)', key))
            or key in ('regions_unexplored:willow_log','regions_unexplored:willow_leaves'))


# These are matching construction details: timber collars, hull ribs, panel
# borders, masonry courses. Coordinates align across a whole original building;
# no random noise, alternate facing loophole or silhouette change is used.
# Tuple order: transverse rib, longitudinal rib, joint cap, vertical collar.
BANDS = {
 'minecraft:spruce_log': ('chipped:reinforced_spruce_log','chipped:carved_stripped_spruce_log',
     'chipped:nailed_spruce_log','chipped:layered_stripped_spruce_log'),
 'minecraft:spruce_planks': ('chipped:framed_spruce_planks','chipped:cross_laced_spruce_planks',
     'chipped:boxed_spruce_planks','chipped:pegged_spruce_planks'),
 'minecraft:spruce_slab': ('minecraft:dark_oak_slab','minecraft:oak_slab',
     'minecraft:stone_brick_slab','minecraft:polished_blackstone_slab'),
 'minecraft:spruce_stairs': ('minecraft:dark_oak_stairs','minecraft:oak_stairs',
     'minecraft:polished_blackstone_stairs','minecraft:polished_blackstone_brick_stairs'),
 'minecraft:cobblestone_stairs': ('minecraft:mossy_cobblestone_stairs','minecraft:andesite_stairs',
     'minecraft:polished_andesite_stairs','minecraft:stone_brick_stairs'),
 'minecraft:oak_fence': ('minecraft:spruce_fence','minecraft:birch_fence',
     'minecraft:jungle_fence','minecraft:acacia_fence'),
 'minecraft:dark_oak_fence': ('minecraft:mangrove_fence','minecraft:dark_oak_fence',
     'minecraft:mangrove_fence','minecraft:dark_oak_fence'),
 'minecraft:calcite': ('chipped:bordered_calcite','chipped:cut_calcite_column',
     'chipped:carved_calcite','chipped:calcite_pillar_top'),
 'minecraft:diorite': ('chipped:bordered_diorite','chipped:cut_diorite_column',
     'chipped:carved_diorite','chipped:diorite_pillar_top'),
 'minecraft:prismarine': ('chipped:bordered_prismarine','chipped:cut_prismarine_column',
     'chipped:carved_prismarine','chipped:prismarine_pillar_top'),
 'minecraft:prismarine_bricks': ('chipped:brick_bordered_prismarine','chipped:prismarine_bricks',
     'chipped:engraved_prismarine','chipped:edged_prismarine_bricks'),
 'minecraft:stripped_spruce_wood': ('chipped:edged_stripped_spruce_log','chipped:reinforced_stripped_spruce_log',
     'chipped:knotted_stripped_spruce_log','chipped:center_cut_spruce_log'),
 'minecraft:spruce_trapdoor': ('chipped:fancy_spruce_trapdoor','chipped:barred_spruce_trapdoor',
     'chipped:classic_windowed_spruce_trapdoor','chipped:iron_barred_spruce_trapdoor'),
}


def architectural_details(geometry, kind, registry):
    """Keep every retained source position, shape and critical orientation."""
    result = {}; changes = []; pending = []
    for pos, original in geometry.items():
        row = deepcopy(original); key = row['Name']; fields = row.setdefault('Properties', {})
        x, y, z = pos
        if key in ('minecraft:spruce_shelf', 'minecraft:dark_oak_shelf'):
            if fields.get('powered') != 'false' or fields.get('waterlogged') != 'false' or fields.get('side_chain') != 'unconnected':
                raise UserError('Only exact dry unpowered original display shelves are reviewed')
            row = {'Name': 'handcrafted:'+key.split(':')[1],
                   'Properties': {'facing': fields['facing'], 'type': '1'}}
            pending.append({'pos': list(pos), 'property': 'shape', 'reason': 'Native Handcrafted neighbor joins after shelf substitution'})
        elif 'glass' in key:
            # The exact imported apertures are retained. The shop's upper sash
            # is a distinct clerestory frame; its glazing is not filled in.
            frame = 'dark_oak' if kind == 'tavern' else 'stripped_spruce_log' if y == 13 else 'spruce'
            row = {'Name': 'mcwwindows:'+frame+'_four_window',
                   'Properties': {'facing': 'east' if kind == 'tavern' else 'north' if z < 12 else 'south',
                                  'windowstate': 'locked'}}
        elif key in BANDS:
            # Three-block bays in X/Z; existing posts gain collar joints every
            # eight vertical blocks. Same-axis runs remain at most seven.
            a, b, c = x % 4 == 3, z % 4 == 3, y % 8 == 7
            # A collar is itself divided at the rib junctions. Swapping the
            # two rib details at this course prevents a collar becoming an
            # unbroken sheet or an X/Z rib becoming a 26-block vertical post.
            selected = ((0 if b and not a else 1 if a and not b else 3) if c
                        else 2 if a and b else 0 if a else 1 if b else None)
            if selected is not None:
                row['Name'] = BANDS[key][selected]
        state_string(row, registry)
        if state_string(row) != state_string(original):
            changes.append({'pos': list(pos), 'before': original, 'after': deepcopy(row),
                            'reason': 'Exact shelf compatibility' if 'shelf' in key else
                                      'Actual framed glazing in preserved aperture' if 'glass' in key else
                                      'Aligned structural rib, panel divider or joint collar'})
        result[pos] = row
    return result, changes, pending


class IntArray(list):
    pass


def snbt(value):
    """Serialize only controlled literal furnishing data, never source commands."""
    if isinstance(value, IntArray):
        return '[I;'+','.join(str(v) for v in value)+']'
    if isinstance(value, dict):
        return '{'+','.join(json.dumps(k)+':'+snbt(v) for k, v in value.items())+'}'
    if isinstance(value, list):
        return '['+','.join(snbt(v) for v in value)+']'
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if type(value) is bool:
        return '1b' if value else '0b'
    if type(value) is int:
        return str(value)
    raise UserError('Unreviewed imported furnishing value')


def safe_tavern_furnishings(tiles, geometry):
    tags = {}; ledger = []
    for pos, tile in tiles.items():
        if pos not in geometry:
            raise UserError('A source furnishing was removed with terrain')
        if tile.get('Items') or tile.get('Lock') or tile.get('Command') or tile.get('LootTable'):
            raise UserError('Nonempty inventories, locks or executable source data require separate review')
        kind = tile.get('id')
        if kind == 'Skull' and tile['SkullType'] == 3:
            owner = tile.get('Owner', {})
            if (set(owner) != {'Id', 'Properties'} or not isinstance(owner['Properties'], dict)
                    or 'textures' not in owner['Properties'] or set(owner['Properties'])-{'textures','Signature'}):
                raise UserError('Unreviewed original skull profile fields')
            try:
                ident = uuid.UUID(owner['Id']); textures = owner['Properties']['textures']
                if not isinstance(textures, list) or len(textures) != 1 or set(textures[0]) != {'Value'}:
                    raise ValueError('Unreviewed texture property')
                texture = textures[0]['Value']
                if not isinstance(texture, str) or len(texture) > 4096:
                    raise ValueError('Texture exceeds finite bound')
                decoded = json.loads(base64.b64decode(texture, validate=True))
                skin = decoded.get('textures', {}).get('SKIN', {})
                url = urlparse(skin.get('url', ''))
                if (url.scheme not in ('http','https') or url.netloc != 'textures.minecraft.net'
                        or not re.fullmatch(r'/texture/[0-9a-fA-F]{32,128}', url.path) or url.query or url.fragment):
                    raise ValueError('Only exact original public Minecraft skin textures are admitted')
            except (ValueError, TypeError, KeyError) as exc:
                raise UserError('The original decorative skull profile is not whitelisted') from exc
            values = [(ident.int >> shift) & 0xffffffff for shift in (96,64,32,0)]
            tag = {'profile': {'id': IntArray([v-(1<<32) if v >= (1<<31) else v for v in values]),
                   'properties': [{'name': 'textures', 'value': texture}]}}
            tags[pos] = snbt(tag)
        elif kind == 'Banner':
            patterns = tile.get('Patterns', [])
            mapping = {'gru':'gradient_up','flo':'flower','sku':'skull'}
            if not isinstance(patterns, list) or len(patterns) > 6:
                raise UserError('Finite original banner patterns required')
            output = []
            for pattern in patterns:
                if (set(pattern) != {'Pattern','Color'} or pattern['Pattern'] not in mapping
                        or type(pattern['Color']) is not int or not 0 <= pattern['Color'] < 16):
                    raise UserError('An unreviewed original banner pattern requires explicit conversion')
                output.append({'pattern': 'minecraft:'+mapping[pattern['Pattern']],
                               'color': LEGACY_DYES[pattern['Color']]})
            if output:
                tags[pos] = snbt({'patterns': output})
        elif kind == 'FlowerPot':
            if tile.get('Item') != 'minecraft:red_flower' or tile.get('Data') != 3:
                raise UserError('Unreviewed original potted flower context')
            # The old block nibble is not the pot's authoritative stored item.
            geometry[pos] = {'Name':'minecraft:potted_azure_bluet'}
        elif kind not in ('Skull','Chest','EnchantTable','Cauldron','Furnace'):
            raise UserError('Unreviewed original block entity '+str(kind))
        ledger.append({'pos':list(pos), 'source_kind':kind,
                       'legacy_profile_properties_retained_in_original_only': ['Signature']
                           if kind == 'Skull' and 'Signature' in tile.get('Owner',{}).get('Properties',{}) else [],
                       'handling':'Whitelisted literal model/profile/pattern conversion' if pos in tags else
                                  'Original empty inventory/default furnishing, or block-state flower/skull context'})
    return tags, ledger


def deferred_tavern_entities(document, source):
    """Retain the four original decor candidates without emitting spawn NBT.

    The old absolute entity coordinates use the recorded WorldEdit selection
    origin. UUIDs, server plugin data, attributes and arbitrary commands are not
    carried forward. The legacy potion still needs an actual item migration.
    """
    origin = tuple(document.get('WEOrigin'+axis) for axis in ('X','Y','Z'))
    if any(type(v) is not int for v in origin):
        raise UserError('Original entity positions require the exact saved selection origin')
    result=[]
    for entity in document.get('Entities',[]):
        kind=entity.get('id')
        if kind not in ('ArmorStand','Painting','ItemFrame'):
            raise UserError('Unreviewed imported entity remains excluded')
        pos=entity.get('Pos',[])
        if len(pos)!=3 or any(type(v) not in (int,float) for v in pos):
            raise UserError('Finite original decor coordinates required')
        local=[pos[i]-origin[i] for i in range(3)]
        if any(not 0<=local[i]<source['size'][i] for i in range(3)):
            raise UserError('Original absolute decor coordinates do not fit the recorded selection')
        note={'source_kind':kind,'local_position':local,
              'proposed_world_position':[local[i]+source['origin'][i] for i in range(3)],
              'status':'DEFERRED ONLY. No source entity or spawn NBT is emitted. Apply only after construction and explicit native review.'}
        if kind=='Painting':
            if entity.get('Motive')!='Courbet' or entity.get('Facing')!=1:
                raise UserError('Unreviewed original painting variant/facing')
            note.update(variant='minecraft:courbet',legacy_hanging_facing=1)
        elif kind=='ItemFrame':
            item=entity.get('Item',{})
            if (set(item)!={'id','Damage','Count'} or item['id'] not in ('minecraft:experience_bottle','minecraft:potion')
                    or type(item['Damage']) is not int or item['Count']!=1):
                raise UserError('Unreviewed original frame item remains excluded')
            note.update(legacy_item=item,legacy_hanging_facing=entity.get('Facing'),
                        item_rotation=entity.get('ItemRotation'),item_conversion='Pending exact native item DFU; do not guess the potion damage')
        else:
            equipment=entity.get('Equipment',[])
            expected=({}, {'id':'minecraft:iron_boots','Damage':0,'Count':1},
                {'id':'minecraft:iron_leggings','Damage':0,'Count':1},
                {'id':'minecraft:iron_chestplate','Damage':0,'Count':1},
                {'id':'minecraft:iron_helmet','Damage':0,'Count':1})
            if equipment!=list(expected):
                raise UserError('Unreviewed original armor display remains excluded')
            note.update(legacy_equipment=equipment,pose=entity.get('Pose',{}),
                        rotation=entity.get('Rotation',[]),show_arms=entity.get('ShowArms'),small=entity.get('Small'))
        result.append(note)
    if len(result)!=4:
        raise UserError('Retain all four original decorative entity candidates separately')
    return result


def prepare(home, assets, flatten, registry_path, backup_id, backup_sha, output):
    home, assets, flatten, registry_path, output = (Path(v).resolve() for v in (home,assets,flatten,registry_path,output))
    if (not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))
            or not output.is_relative_to(home/'staging') or output.exists()):
        raise UserError('Owned artistic home and a NEW bounded private output are required')
    admission = guard(4*1024**2, MAX_OUTPUT)
    if not registry_path.is_file() or registry_path.stat().st_size > 8*1024**2:
        raise UserError('A bounded actual native registry is required')
    if digest(flatten) != FLATTEN_SHA:
        raise UserError('The authenticated exact native 128-state flattening result is required')
    registry = read_json(registry_path)
    if not Path(registry['world_path']).resolve().is_relative_to(home/'world'):
        raise UserError('The actual registry must belong to this private world')
    receipt = read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or receipt.get('id') != backup_id or receipt.get('sha256') != backup_sha:
        raise UserError('Explicit current stopped checkpoint required')
    snapshot = BackupWorld(home, receipt, registry); documents = {}; summaries = []
    def encode(name, value):
        raw = (json.dumps(value, separators=(',',':'), ensure_ascii=False)+'\n').encode()
        if sum(map(len, documents.values()))+len(raw)>MAX_OUTPUT:
            raise UserError('The finite private import output exceeds its bound')
        documents[name] = raw
        return hashlib.sha256(raw).hexdigest()
    try:
        for kind, source in ORIGINALS.items():
            path = assets/source['file']
            if path.stat().st_size != source['bytes'] or digest(path) != source['sha256']:
                raise UserError('Keep the exact named original bytes for '+source['name'])
            original = read_source(path); tags = {}; notes = {}
            if kind == 'tavern':
                decoded, tiles, notes = contextual_legacy(original, read_json(flatten))
                geometry = {p:v for p,v in decoded.items() if v['Name'] not in IMPORTED_TERRAIN}
                tags, furnishings = safe_tavern_furnishings(tiles, geometry)
                notes['furnishings'] = furnishings
                notes['deferred_original_decor'] = deferred_tavern_entities(original,source)
                notes['imported_terrain_air_water_excluded'] = len(decoded)-len(geometry)
            else:
                decoded = litematic_geometry(original)
                geometry = {p:v for p,v in decoded.items() if v['Name'] not in VOID}
                tiles = [v for reg in original['Regions'].values() for v in reg.get('TileEntities', [])]
                if len(geometry) != 1779 or len(tiles) != 117 or any(v.get('Items') or v.get('components')
                        or any(s for face in ('front_text','back_text') for s in v.get(face,{}).get('messages',[])) for v in tiles):
                    raise UserError('The reviewed exact empty/default shop furnishings changed')
                notes = {'source_entities_excluded':sum(len(r.get('Entities',[])) for r in original['Regions'].values()),
                         'source_block_entities':len(tiles), 'empty_default_furnishings_preserved':True,
                         'shelf_palette_states':6, 'placed_shelves':35}
            adapted, changes, pending = architectural_details(geometry, kind, registry)
            local = {p:state_string(v, registry) for p,v in adapted.items()}
            checks = require_material_rule(local, source['name']+' complete adapted original')
            transformed = {}; transformed_tags = {}; origin=source['origin']
            for p, value in adapted.items():
                q = rotate_position(p,source['size'],source['turns'])
                q = tuple(q[i]+origin[i] for i in range(3))
                transformed[q] = state_string(rotate_record(value,source['turns']),registry)
                if p in tags: transformed_tags[q] = tags[p]
            before = {}; cleared = []
            a,b,c,d = source['bounds']
            # Clear only authorized ordinary trees inside the exact reserved
            # footprint; no outside canopy, bee nest or saved BE is touched.
            for x in range(a,c+1):
                for z in range(b,d+1):
                    for y in range(64,108):
                        pos=x,y,z; old=snapshot.state(pos); key=base(old)
                        if pos in snapshot.protected:
                            raise UserError('Preserve saved block entity in reserved import plot')
                        if ordinary_tree(key):
                            cleared.append({'pos':list(pos),'old':old,
                                            'handling':'Original architectural target' if pos in transformed else 'Bounded ordinary tree clearance'})
                            if pos not in transformed:transformed[pos]=AIR
                        elif key not in VOID and not ordinary_tree(key) and not plant(key):
                            raise UserError('Reserved dry import plot contains unreviewed construction/fluid: '+str(pos)+' '+key)
            # A low masonry shoe follows only actual ground-floor load points.
            # It may bridge one air block above dry soil, never fill the whole
            # rectangle, replace water, or turn roof overhangs into columns.
            columns={}
            for p,value in transformed.items():
                if value!=AIR:columns.setdefault((p[0],p[2]),[]).append(p)
            footings=[]
            for (x,z),cells in columns.items():
                low=min(p[1] for p in cells)
                if low!=64:continue
                key=base(transformed[x,low,z])
                if (not key.startswith('minecraft:') and not key.startswith('chipped:')
                        or any(word in key for word in ('fence','trapdoor','pane','sign','head','skull','pot','torch','shelf'))):
                    continue
                below=x,63,z;state=snapshot.state(below)
                if base(state) in NATURAL:continue
                if base(state) not in VOID and not plant(base(state)):
                    raise UserError('A source floor has no reviewed dry footing')
                if base(snapshot.state((x,62,z))) not in NATURAL or below in snapshot.protected:
                    raise UserError('Relocate instead of creating a deep platform under the original')
                a_joint,b_joint=(x-origin[0])%4==3,(z-origin[2])%4==3
                key=('chiseled_stone_bricks' if a_joint and b_joint else 'mossy_stone_bricks'
                     if a_joint else 'cracked_stone_bricks' if b_joint else 'stone_bricks')
                transformed[below]='minecraft:'+key
                footings.append({'pos':list(below),'state':transformed[below],'supports':list((x,64,z))})
            checks=require_material_rule({p:v for p,v in transformed.items() if v!=AIR},
                                         source['name']+' adapted original including actual-ground masonry shoes')
            for pos, value in transformed.items():
                old=snapshot.state(pos); key=base(old)
                if pos in snapshot.protected or key not in NATURAL|VOID and not plant(key) and not ordinary_tree(key):
                    raise UserError('Preserve unrelated saved construction, fluid or furnishing: '+str(pos))
                before[pos]=old
            def payload(states, name, include_tags=False):
                palette=sorted(set(states.values())); indexes={s:n for n,s in enumerate(palette)}
                return {'format':'awft-native-settlement:1','name':name,'created':utcnow(),
                    'seed':registry['seed'],'world_path':registry['world_path'],'backup_sha256':backup_sha,
                    'bounds':list(source['bounds']),'palette':palette,
                    'blocks':[[*p,indexes[v]] for p,v in sorted(states.items())],
                    'block_entities':[{'pos':list(p),'nbt':v} for p,v in sorted(transformed_tags.items())] if include_tags else [],
                    'commands':[],'landmarks':[],
                    'validation':'STAGED ORIGINAL ADAPTATION; actual native neighbor updates/readback and visual review required'}
            plan_sha=encode(kind+'-adapted.json',payload(transformed,source['name']+' - exact original adapted for reserved dry site',True))
            before_sha=encode(kind+'-native-before.json',payload(before,'VERIFY ONLY - exact saved import-site preimage'))
            summaries.append({'kind':kind,'source':source,'retained_source_positions':len(geometry),
                'architectural_substitutions':len(changes),'substitutions':changes,'native_pending':pending,
                'source_context':notes,'tree_clearance':cleared,'targets':len(transformed),
                'dry_ground_footings':footings,
                'new_literal_furnishing_tags':len(tags),'material_rule':checks,
                'plan_sha256':plan_sha,'before_sha256':before_sha,
                'identity':'The exact original occupied-cell silhouette and all retained architectural positions are preserved',
                'native_status':'Not placed; native models, joined states, literal tags, support and routes require actual staging review'})
        sources=snapshot.sources.copy()
    finally:
        snapshot.close()
    manifest={'format':'awft-requested-original-adaptations:1','created':utcnow(),
        'source_sha256':digest(Path(__file__)),'decoder_sha256':digest(Path(__file__).with_name('structure_import.py')),
        'registry_sha256':digest(registry_path),'native_flatten_sha256':FLATTEN_SHA,
        'native_flatten_classpath_receipt_sha256':digest(flatten.parent/'classpath-provenance.json'),
        'checkpoint_id':backup_id,'checkpoint_sha256':backup_sha,'saved_sources':sources,
        'buildings':summaries,'reserve_guard':admission,'native_actions':0,'world_writes':0,
        'entity_imports':0,'source_command_execution':False,
        'release_policy':'Original downloads and private geometry remain outside Git; public source contains recipes, attribution and synthetic fixtures only'}
    manifest_sha=encode('manifest.json',manifest)
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in documents.items():(output/name).write_bytes(raw)
    return {'output':str(output),'manifest_sha256':manifest_sha,'buildings':[
        {k:s[k] for k in ('kind','targets','retained_source_positions','architectural_substitutions','plan_sha256','before_sha256')}
        for s in summaries],'bytes':sum(map(len,documents.values())),'native_actions':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for field in ('home','assets','flatten','registry','output'):parser.add_argument('--'+field,type=Path,required=True)
    parser.add_argument('--backup-id',required=True);parser.add_argument('--backup-sha256',required=True)
    a=parser.parse_args()
    print(json.dumps(prepare(a.home,a.assets,a.flatten,a.registry,a.backup_id,a.backup_sha256,a.output),indent=2))
