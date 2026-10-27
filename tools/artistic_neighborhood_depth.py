"""An original architectural depth layer over the twenty furnished houses.

Pure composites remain immutable. This module authors bounded surface geometry
only; native preimages/admission require a separate current stopped checkpoint.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from control_room.common import UserError, digest, read_json
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_street import designs
from tools.artistic_street_surfaces import construct as signal
from tools.artistic_cottage_lights import construct as court
from tools.artistic_craft_details import construct as bramble
from tools.artistic_cottages import BUILDINGS as COTTAGES
from tools.artistic_craft_lane import lots
from tools.artistic_bridge_refinement import encoded, flatten, payload
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, base, properties

AIR = 'minecraft:air'
MIB = 1024**2
MAX_OUTPUT = 16*MIB
ARTWORK = {
    'signal':('0b60dbc2a9d15519e5dc31d99a8f8c72bf9df89d8cab8059e5458506d4e8c174','8ebbf9cfc3227a192b664a5e68a332d061842cb23de8957f740d68702817240d'),
    'court':('a3ac40ae53d433cf439d540d33c431c3469cd99925babcf5355221af64a1978b','b8dc101a4dd92fba50569dde4e837e08513b21f630454e5f944dc1d0cba2b1fe'),
    'bramble':('5a6105aee9b5557c29b31acc02141ed308175f59796aa35cd5328adbfe6dd955','edb24e9fc2b327108ab26d409e61bfb14d6eefaac791e4599ef7f0826577f99e'),
}
VECTORS = {'north': (0, -1), 'south': (0, 1), 'east': (1, 0), 'west': (-1, 0)}
ROOF_SUPPORT = {'dark_oak':'charred_spruce','spruce':'spruce','oak':'waxed_acacia','birch':'waxed_acacia'}
STRUCTURE = {'minecraft:'+name for name in ('bricks', 'stone_bricks', 'mossy_stone_bricks', 'calcite',
             'white_terracotta', 'yellow_terracotta', 'cyan_terracotta', 'green_terracotta', 'light_gray_terracotta',
             'oak_planks', 'spruce_planks', 'birch_planks', 'dark_oak_planks', 'dark_oak_wood',
             'stripped_dark_oak_log', 'stripped_spruce_log', 'stripped_oak_log', 'stripped_birch_log',
             'stripped_oak_wood', 'stripped_dark_oak_wood', 'stripped_spruce_wood', 'chiseled_stone_bricks')}
STRUCTURE.update({'dawnoftimebuilder:'+name for name in ('plastered_stone', 'green_plastered_stone', 'blue_plastered_stone')})


@dataclass(frozen=True)
class Design:
    district: str
    ident: str
    name: str
    window: tuple  # first pane x, top-window y, z, outward face, hood width
    hood: str
    wood: str
    corner: tuple  # x,z, floor, native relief style, outward face
    axis: str
    stations: tuple  # explicit interior beam stations measured from room bounds
    intent: str


DESIGNS = (
    Design('signal','chandler','The Copper Lantern',(4,7,20,'south',3),'slant','dark_oak',(2,8,0,'brace','west'),'x',(3,7),'A short angled lamp-window brow and timber knee lighten the chandler jetty while retaining the next-storey planted box; lamp-making rooms gain measured cross ribs.'),
    Design('signal','sailmaker','Seven Stitches',(13,7,17,'south',3),'slant','spruce',(11,6,0,'chamfer','west'),'z',(3,5),'An angled loft hood and a chamfered stone foot recall the sail loft; long ceiling ribs follow canvas cutting direction.'),
    Design('signal','inn',"The Wren's Wake",(23,7,16,'south',3),'arch','oak',(21,7,0,'carved','north'),'x',(3,6),'Paired pointed arch heads mark the dining room above the tavern; carved corner supports and bar-room coffers break the L-plan masses.'),
    Design('signal','fishmonger','Tide & Scale',(37,7,19,'south',3),'masonry','spruce',(35,11,0,'chamfer','west'),'z',(3,5),'A modest stepped masonry brow and cut corner create a weathered fish-shop loggia without extending the market awning.'),
    Design('signal','harbormaster','The Sounding House',(47,8,21,'south',3),'lintel','dark_oak',(46,11,1,'carved','north'),'x',(3,6),'A crisp chart-room lintel and carved stone corner articulate the official harbor office; overhead ribs echo chart-desk bays.'),
    Design('signal','bookbinder','Ink & Bramble',(5,8,24,'north',3),'arch','spruce',(10,35,1,'brace','east'),'z',(3,6),'An intimate pointed reading-window hood and timber return frame the recessed upper reading room; no retired giant projection returns.'),
    Design('signal','apothecary','The Glass Rosemary',(14,7,34,'south',3),'slant','oak',(20,34,0,'niche','east'),'x',(3,7),'A fine sloping garden herb-window eyebrow and shallow carved corner niche preserve the planted street projection while adding actual shadow lines to the rear elevation.'),
    Design('signal','archhouse','Needle Court House',(26,7,23,'north',3),'masonry','spruce',(32,24,0,'carved','east'),'z',(3,6),'A stepped courtyard brow and carved passage corner retain the two-wide alley; overhead structure is kept high above its route.'),
    Design('signal','lodging','The Blue Thread',(39,7,24,'north',3),'lintel','oak',(44,37,0,'brace','east'),'x',(3,7),'A thin balcony lintel and angled sailor-house corner create depth without another low canopy above the lane.'),
    Design('signal','keeper','Rose Compass Studio',(49,8,26,'north',3),'lintel','spruce',(48,38,1,'niche','south'),'z',(3,6),'A small painter-studio eyebrow and recessed timber corner emphasize the narrow quay-view house while retaining its upper shutters instead of adding a broad upper box.'),
    Design('court','couple',COTTAGES[0],(4,8,8,'west',2),'integrated_arch','oak',(3,5,1,'chamfer','west'),'x',(3,6),'A delicate pointed bedroom surround shaped into the existing edge cap and a chamfered hearth-side corner complement the furnished couple home; lower ceiling ribs stay above its cozy seating.'),
    Design('court','bakehouse',COTTAGES[1],(29,3,9,'west',2),'masonry','birch',(37,15,0,'chamfer','east'),'z',(3,5),'A short stone oven-window brow and shaped bakehouse corner create a sheltered bread-window character; the sleeping loft stays clear.'),
    Design('court','weaver',COTTAGES[2],(8,3,27,'north',2),'slant_low','spruce',(7,34,0,'brace','west'),'x',(3,5),'A low-profile angled brow sits below the existing roof edge; narrow timber knees frame the loom cottage instead of a second awning.'),
    Design('court','glasshouse',COTTAGES[3],(34,3,27,'north',1),'entry_relief','birch',(31,27,0,'carved','north'),'x',(3,),'A carved corner and thinner original opaque rafters give the greenhouse depth while preserving its existing door lintel, every glazed skylight and window.'),
    Design('bramble','cobbler','Bramble & Buckle',(4,7,20,'south',2),'arch','dark_oak',(2,9,0,'brace','north'),'x',(3,6),'A pointed reading-bay eyebrow and a leather-shop timber knee sharpen the cobbler facade; compact workroom coffers preserve shelves and signs.'),
    Design('bramble','luthier','Wren & Reed',(13,6,15,'south',2),'slant','oak',(12,5,-1,'niche','west'),'z',(3,5),'A little angled music-room brow and recessed corner register break the tall green house while retaining its stepped upper setback; longitudinal ribs follow its instrument benches.'),
    Design('bramble','potter','Clay & Candle',(26,5,17,'south',2),'masonry','birch',(25,7,-2,'carved','north'),'x',(3,6),'A stepped pottery-window brow and carved kiln-side foot distinguish the blue plaster shop; small ceiling bays leave the candle displays intact.'),
    Design('bramble','glazier','Copper & Glass',(36,6,25,'south',2),'slant','spruce',(35,17,-1,'chamfer','north'),'z',(3,5),'An angled glazing-shop cap and cut stone corner emphasize the inset window bay with a restrained one-block projection.'),
    Design('bramble','grocer','The Clover Pantry',(4,7,25,'north',2),'lintel','oak',(10,33,0,'niche','east'),'x',(3,5),'A fine pantry lintel and carved family-house corner give the open produce loggia a lighter upper edge, with kitchen coffers above working height.'),
    Design('bramble','stoneleaf','The Stoneleaf Workshop',(19,2,25,'north',2),'masonry_low','spruce',(18,34,-1,'carved','west'),'x',(3,6),'A low stepped stone brow and fluted mason corner make the single-storey workshop feel carved; roof and work-bench headroom remain clear.'),
)

# Compass corners are authored separately for each silhouette, including its
# stepped upper floors. They are not a repeated complete facade/house stamp.
CORNER_FIELDS = {
    'chandler':('nw','se'),'sailmaker':('nw','ne'),'inn':('nw','ne','se'),
    'fishmonger':('nw','sw'),'harbormaster':('ne','sw'),'bookbinder':('ne','sw'),
    'apothecary':('se','sw'),'archhouse':('ne','se'),'lodging':('nw','se'),'keeper':('ne','se'),
    'couple':('nw','ne'),'bakehouse':('ne','se'),'weaver':('nw','sw'),'glasshouse':('nw','se'),
    'cobbler':('nw','ne'),'luthier':('nw','ne','se'),'potter':('nw','ne'),
    'glazier':('nw','sw'),'grocer':('ne','se'),'stoneleaf':('nw','sw','se'),
}
NICHE_FACES = {
    'chandler':('north','east'),'sailmaker':('south','west'),'inn':('south','east'),
    'fishmonger':('south','west'),'harbormaster':('south','east'),'bookbinder':('north','west'),
    'apothecary':('south','west'),'archhouse':('north','east'),'lodging':('north','east'),'keeper':('north','west'),
    'couple':('south','west'),'bakehouse':('north','east'),'weaver':('north','south'),'glasshouse':(),
    'cobbler':('south','west'),'luthier':('south','east'),'potter':('south','west'),
    'glazier':('south','east'),'grocer':('north','east'),'stoneleaf':('north','west'),
}
NICHE_MATERIAL = {
    'chandler':'dark_oak','sailmaker':'spruce','inn':'smooth_sandstone','fishmonger':'brick',
    'harbormaster':'stone_brick','bookbinder':'dark_oak','apothecary':'smooth_sandstone',
    'archhouse':'stone_brick','lodging':'oak','keeper':'spruce','couple':'smooth_sandstone',
    'bakehouse':'smooth_sandstone','weaver':'spruce','glasshouse':'stone_brick',
    'cobbler':'dark_oak','luthier':'oak','potter':'smooth_sandstone','glazier':'brick',
    'grocer':'smooth_sandstone','stoneleaf':'stone_brick',
}
INFILL = {key for key in STRUCTURE if not any(token in key for token in ('planks','_wood','_log'))}


class District:
    def __init__(self, name, composed, buildings):
        self.name, self.composed = name, composed
        self.base, self.p = composed.p, copy.deepcopy(composed.p)
        self.names = set(buildings)
        self.protected = set(self.base.tags)
        self.body = set()
        self.supports, self.effects, self.changed_by = [], [], {}
        for pos, state in self.base.blocks.items():
            key = base(state)
            if key != AIR and key not in STRUCTURE:
                self.protected.add(pos)  # includes default/unwritten inventory, furniture, glazing, fixtures and roofs
            if key.endswith('_stairs') or key.startswith('mcwdoors:'):
                self.protected.update((pos[0],pos[1]+dy,pos[2]) for dy in (0,1,2))
            if key.startswith(('mcwlights:', 'supplementaries:')) or key.endswith('_wall_sign'):
                face = properties(state).get('facing')
                if face in VECTORS:
                    dx,dz = VECTORS[face];self.protected.add((pos[0]-dx,pos[1],pos[2]-dz))
            if key.endswith(('_hanging_sign','_lantern')) or key == 'minecraft:chain':
                self.protected.add((pos[0],pos[1]+1,pos[2]))
        points = set(self.base.navigation)
        for route in self.base.routes:
            points.update(tuple(math.floor(v) for v in point) for point in route['local_player_feet'])
        for x,y,z in points:
            self.body.update(((x,y,z),(x,y+1,z)))
            self.protected.update(((x,y-1,z),(x,y,z),(x,y+1,z)))
        self.current = None

    def start(self, design):
        self.current = design
        self.effects.append({'id':design.ident,'name':design.name,'intent':design.intent,'changes':{},'ceiling_rooms':[]})

    def put(self, pos, key, *, reason, replace=False, support=None, **props):
        pos=tuple(pos);old=self.base.blocks.get(pos,AIR)
        if pos in self.protected or pos in self.body:
            raise UserError('Preserve current BE/window/furniture/route/support at '+self.name+' '+str(pos)+' '+old)
        owner=self.base.owners.get(pos)
        if owner in self.names and owner!=self.current.name:
            raise UserError('Preserve the neighboring complete building: '+str((pos,owner)))
        if old != AIR and (not replace or base(old) not in STRUCTURE):
            raise UserError('No authored structural authority at '+str((self.current.ident,pos,old)))
        world=tuple(pos[i]+self.p.origin[i] for i in range(3))
        if getattr(self.base,'mask',{}).get(world) or world in getattr(self.base,'existing_block_entities',set()):
            raise UserError('Preserve exact bridge/cottage exclusion, including air')
        if support is not None:
            backing=self.base.blocks.get(tuple(support),AIR)
            if base(backing) not in STRUCTURE | {'minecraft:'+wood+'_slab' for wood in ('oak','spruce','birch','dark_oak')}:
                raise UserError('No original structural support for '+str((self.current.ident,pos,tuple(support),backing)))
            self.supports.append({'detail':list(pos),'existing_support':list(support),'reason':reason})
        state=self.p.state(key,**props)
        if pos in self.changed_by and self.p.blocks[pos]!=state:
            raise UserError('Two architectural roles overlap: '+str((self.current.ident,pos)))
        self.p.blocks[pos]=state;self.p.owners[pos]=self.current.name
        self.p.uses.setdefault(key.split(':')[0],set()).add(self.current.name)
        self.changed_by[pos]=self.current.ident
        self.effects[-1]['changes'].setdefault(reason,[]).append(list(pos))

    def beam(self,pos,axis,wood,*,reason,support=None,slab=False,replace=False):
        props={'pillar_connection':'nothing','waterlogged':False}
        if not slab:props.update(axis=axis,subaxis=False)
        self.put(pos,'dawnoftimebuilder:'+wood+('_support_slab' if slab else '_support_beam'),
                 reason=reason,support=support,replace=replace,**props)


def facade(d, design):
    x,y,z,face,width=design.window;dx,dz=VECTORS[face]
    tx,tz=(1,0) if face in ('north','south') else (0,1)
    if design.hood=='entry_relief':
        d.effects[-1]['protected_entrance_lintel_retained']=True
        return
    # The chosen original native windows remain byte-for-byte untouched. A
    # narrow projecting brow is anchored to their original opaque head band.
    for n in range(width):
        pane=(x+tx*n,y,z+tz*n)
        if not d.base.blocks.get(pane,AIR).startswith('mcwwindows:'):
            raise UserError('Authored native window anchor changed: '+str((design.ident,pane)))
    hy=y if design.hood.endswith('_low') else y+1
    for n in range(width):
        pos=(x+tx*n+dx,hy,z+tz*n+dz);back=(pos[0]-dx,hy,pos[2]-dz)
        # Low brows sit in front of the retained top pane and hang from the
        # original solid header above; they never use glass as a support.
        if design.hood.endswith('_low'):back=(x+tx*n,hy+1,z+tz*n)
        style=design.hood.removesuffix('_low').removeprefix('integrated_')
        replacing=design.hood.startswith('integrated_')
        if style in ('slant','pediment'):
            d.put(pos,'dawnoftimebuilder:'+ROOF_SUPPORT[design.wood]+'_roof_support',reason='short angled hood with retained native glass',support=back,
                  facing={'north':'south','south':'north','east':'west','west':'east'}[face],type='top',shape='straight',waterlogged=False)
        elif style=='masonry':
            d.put(pos,'minecraft:stone_brick_stairs',reason='short stepped masonry window brow',support=back,
                  facing={'north':'south','south':'north','east':'west','west':'east'}[face],half='top',shape='straight',waterlogged=False)
        elif style=='arch':
            d.put(pos,'mythrais:single_gothic_arch_upper_dark_oak',reason='small pointed arch head above the retained native window',support=back,replace=replacing,
                  facing=face,colour=0,shape='0')
        else:
            d.beam(pos,'x' if tx else 'z',design.wood,reason='fine projecting modeled window lintel',support=back)
    if design.hood=='pediment':
        n=width//2;pos=(x+tx*n+dx,hy+1,z+tz*n+dz)
        d.beam(pos,'x' if tx else 'z',design.wood,reason='small raised pediment crown',support=(pos[0]-dx,pos[1],pos[2]-dz),slab=True)


def corner(d, design):
    x,z,floor,style,face=design.corner
    for y in (floor+2,floor+3):
        pos=(x,y,z)
        if style=='carved':
            d.put(pos,'mythrais:spiral_column_stone',reason='carved recessed corner between retained foot and head band',replace=True,facing=face,colour=1)
        elif style=='brace':
            d.put(pos,'dawnoftimebuilder:'+ROOF_SUPPORT[design.wood]+'_roof_support',reason='angled timber knee carved into the old flat corner',replace=True,
                  facing=face,type='bottom' if y==floor+2 else 'top',shape='straight',waterlogged=False)
        elif style=='niche':
            d.beam(pos,'x' if face in ('north','south') else 'z',design.wood,reason='half-depth corner recess and carved register',slab=y==floor+3,replace=True)
        else:
            d.put(pos,'minecraft:stone_brick_stairs',reason='chamfered masonry corner and cap',replace=True,
                  facing=face,half='bottom' if y==floor+2 else 'top',shape='straight',waterlogged=False)


def articulated_storey_corners(d, design):
    for room in d.base.rooms:
        if room['building'] not in (design.ident,design.name):continue
        outline={tuple(v) for v in room['outline']};f=room['local_floor_y']
        row={'level':room['level'],'corners':[]}
        for compass in CORNER_FIELDS[design.ident]:
            sx=-1 if 'w' in compass else 1;sz=-1 if 'n' in compass else 1
            x,z=max(outline,key=lambda p:(sx*p[0]+sz*p[1],sx*p[0],sz*p[1]))
            face='west' if sx<0 else 'east';count=0
            # Only convex original solid corner fields are articulated. Fixture
            # supports, glass and hollow/stepped-away corners remain untouched.
            if (x+sx,z) in outline or (x,z+sz) in outline:continue
            for y in (f+2,f+3):
                pos=(x,y,z)
                if pos in d.protected or pos in d.changed_by or base(d.base.blocks.get(pos,AIR)) not in STRUCTURE:continue
                style=design.corner[3]
                if style=='carved':
                    d.put(pos,'mythrais:spiral_column_stone',reason='carved convex storey corner with retained solid bands',replace=True,facing=face,colour=1)
                elif style=='brace':
                    d.put(pos,'dawnoftimebuilder:'+ROOF_SUPPORT[design.wood]+'_roof_support',reason='shaped timber knee at a selected convex storey corner',replace=True,
                          facing=face,type='bottom' if y==f+2 else 'top',shape='straight',waterlogged=False)
                elif style=='niche':
                    d.beam(pos,'z',design.wood,reason='recessed convex storey-corner register',replace=True,slab=y==f+3)
                else:
                    d.put(pos,'minecraft:stone_brick_stairs',reason='dressed chamfer at a selected convex storey corner',replace=True,
                          facing=face,half='bottom' if y==f+2 else 'top',shape='straight',waterlogged=False)
                count+=1
            # A single modeled knee projects from the retained opaque head band;
            # this is a corner support, never a continuous new lane awning.
            pos=(x+sx,f+4,z);support=(x,f+4,z)
            if (pos not in d.protected and pos not in d.changed_by and d.base.blocks.get(pos,AIR)==AIR
                    and base(d.base.blocks.get(support,AIR)) in STRUCTURE
                    and d.base.owners.get(pos) not in d.names-{design.name}):
                d.put(pos,'dawnoftimebuilder:'+ROOF_SUPPORT[design.wood]+'_roof_support',reason='one-cell supported corner cornice knee',support=support,
                      facing=face,type='top',shape='straight',waterlogged=False)
                count+=1
            row['corners'].append({'compass':compass,'at':[x,z],'modeled_cells':count})
        d.effects[-1].setdefault('articulated_storeys',[]).append(row)


def ceilings(d, design):
    for room in d.base.rooms:
        if room['building'] not in (design.ident,design.name):continue
        outline={tuple(v) for v in room['outline']};f=room['local_floor_y'];axis=design.axis
        lo=min(v[1 if axis=='x' else 0] for v in outline)
        chosen={lo+station for station in design.stations}
        count=0
        minx=min(v[0] for v in outline);minz=min(v[1] for v in outline)
        for x,z in sorted(outline):
            if (z if axis=='x' else x) not in chosen:continue
            if any((x+dx,z+dz) not in outline for dx,dz in ((1,0),(-1,0),(0,1),(0,-1))):continue
            pos=(x,f+3,z);above=(x,f+4,z)
            # Sensible source-bound ceiling fields: do not fill a vault, shade
            # a skylight, bury a fixture or touch the original stairs/headroom.
            if (pos in d.protected or d.base.blocks.get(pos,AIR)!=AIR
                    or base(d.base.blocks.get(above,AIR)) not in STRUCTURE):continue
            station=(x-minx) if axis=='x' else (z-minz)
            d.beam(pos,axis,design.wood,reason='supported half-height ceiling coffer beneath the existing opaque floor',
                   support=above,slab=station%4==0)
            count+=1
        d.effects[-1]['ceiling_rooms'].append({'level':room['level'],'floor':f,'modeled_cells':count,
             'preserved_vault_or_fixture_gaps':True,'authority':'Actual original opaque support above each new rib; source headroom only'})


def blind_wall_recesses(d, design):
    # A paired bottom/top stair retains a continuous solid BACK half. Its outer
    # half has an inset sill and head: real half-block-deep blind architecture,
    # not a new opening through the wall, material-only trim or a wider awning.
    for room in d.base.rooms:
        if room['building'] not in (design.ident,design.name):continue
        outline={tuple(v) for v in room['outline']};f=room['local_floor_y']
        minx=min(x for x,z in outline);minz=min(z for x,z in outline)
        count=0
        for face in NICHE_FACES[design.ident]:
            dx,dz=VECTORS[face]
            for x,z in sorted(outline):
                if (x+dx,z+dz) in outline:continue
                # Three-metre framed bays are already present in the original
                # facades. The first infill register between posts is explicit.
                if ((x-minx) if dx==0 else (z-minz))%3!=1:continue
                pair=((x,f+2,z),(x,f+3,z))
                if any(pos in d.protected or pos in d.changed_by or base(d.base.blocks.get(pos,AIR)) not in INFILL for pos in pair):continue
                for n,pos in enumerate(pair):
                    d.put(pos,'minecraft:'+NICHE_MATERIAL[design.ident]+'_stairs',reason='half-block blind wall recess between the retained original posts',replace=True,
                          facing={'north':'south','south':'north','east':'west','west':'east'}[face],
                          half='bottom' if n==0 else 'top',shape='straight',waterlogged=False)
                    count+=1
        d.effects[-1].setdefault('blind_recesses',[]).append({'level':room['level'],'modeled_cells':count,
                 'solid_back_half_retained':True,'windows_fixtures_and_structural_posts_preserved':True})


def glass_rafters(d, design):
    if design.ident!='glasshouse':return
    for pos,state in sorted(d.base.blocks.items()):
        if d.base.owners[pos]!=design.name or pos[1]<4:continue
        key=base(state)
        if key not in ('minecraft:birch_planks','minecraft:stripped_oak_wood'):continue
        # Replace the opaque rafter cross-section itself; every original glass
        # cell and all potting benches/planters remain exact and unobscured.
        if pos in d.protected:continue
        d.beam(pos,'x' if key.endswith('_planks') else 'z','birch' if key.endswith('_planks') else 'oak',
               reason='modeled original opaque greenhouse rafter; all skylight glass retained',replace=True)


def construct(registry,cottage_survey,craft_survey,exclusions):
    districts={'signal':District('signal',signal(registry)[0],[b.name for b in designs()]),
               'court':District('court',court(registry,cottage_survey)[0],COTTAGES),
               'bramble':District('bramble',bramble(registry,craft_survey,exclusions),[b.name for b in lots()])}
    if len(DESIGNS)!=20 or len({(v.district,v.ident) for v in DESIGNS})!=20:
        raise UserError('Every one of the twenty houses needs an explicit authored design')
    for design in DESIGNS:
        d=districts[design.district];d.start(design)
        facade(d,design);corner(d,design);articulated_storey_corners(d,design)
        blind_wall_recesses(d,design);ceilings(d,design);glass_rafters(d,design)
    check(districts)
    return districts


def check(districts):
    checks={}
    for name,d in districts.items():
        if d.p.tags!=d.base.tags:raise UserError('An existing inventory/sign/BE payload changed')
        changed={pos for pos,state in d.p.blocks.items() if state!=d.base.blocks.get(pos,AIR)}
        if changed & d.protected:raise UserError('Protected opening, furniture, headroom or support changed')
        if not changed<=set(d.changed_by):raise UserError('A changed cell has no explicit authored architectural role')
        if not 0<len(changed)<=5000:raise UserError('Neighborhood depth allocation exceeded')
        if set(d.changed_by.values())!={v.ident for v in DESIGNS if v.district==name}:
            raise UserError('A neighborhood building has no physical depth changes')
        materials=[require_material_rule({pos:state for pos,state in d.p.blocks.items() if d.p.owners[pos]==building},building)
                   for building in sorted(d.names)]
        require_outdoor_rule(d.p.blocks,name+' complete authored streets, gardens and architecture')
        for pos in d.body:
            if d.p.blocks.get(pos,AIR)!=d.base.blocks.get(pos,AIR):raise UserError('An exact original walking body cell changed')
        for pos,state in d.base.blocks.items():
            if 'glass' in base(state) and d.p.blocks.get(pos,AIR)!=state:raise UserError('A skylight/window glass cell changed')
        for row in d.supports:
            pos=tuple(row['existing_support'])
            if d.p.blocks.get(pos,AIR)!=d.base.blocks.get(pos,AIR):raise UserError('An architectural detail lost its exact retained support')
        checks[name]={'buildings':len(d.names),'changed_positions':len(changed),'material_checks':materials,
                      'all_authored_runs_at_most_nine':True,'preserved_tagged_BEs':len(d.base.tags),
                      'preserved_body_cells':len(d.body),'native_walking_and_artistic_acceptance':'pending'}
    return checks


def author(home,registry_path,cottage_survey_path,craft_survey_path,exclusion_paths,output):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging') or len(exclusion_paths)!=3:
        raise UserError('New private artwork directory and all three original exclusion plans required')
    reserve=guard(4*MIB,MAX_OUTPUT)
    registry=read_json(registry_path)
    exclusions=[(name,read_json(path),digest(Path(path))) for name,path in zip(('cottage','bascule','rosebridge'),exclusion_paths)]
    districts=construct(registry,read_json(cottage_survey_path),read_json(craft_survey_path),exclusions)
    checks=check(districts);raw={};manifests={}
    for name,d in districts.items():
        changed={pos:state for pos,state in d.p.blocks.items() if state!=d.base.blocks.get(pos,AIR)}
        geometry={'format':'awft-neighborhood-depth-geometry:1','district':name,'local_origin':list(d.p.origin),
                  'changes':[[*pos,state] for pos,state in sorted(changed.items())],
                  'authority':'ARTWORK ONLY; no current saved preimage or native placement admission'}
        raw[name+'-geometry.json']=encoded(geometry)
        full=d.p.serialize('0'*64);full.update(verification_only=True,name=name+' complete depth composition UNBOUND')
        raw[name+'-full-verification-UNBOUND.json']=encoded(full)
        manifests[name]={'checks':checks[name],'buildings':d.effects,'supports':d.supports,
                         'native_preimage_and_saved_default_BE_gate':'pending current stopped checkpoint'}
    manifest={'format':'awft-neighborhood-depth-artwork:1','source_sha256':digest(Path(__file__)),'buildings':20,
              'composites':['artistic_street_surfaces','artistic_cottage_lights','artistic_craft_details'],
              'districts':manifests,'reserve_guard':reserve,'native_actions':False,'existing_BE_replays':0,
              'files':{name:{'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()} for name,value in raw.items()},
              'gate':'Saved and fresh native before/after verification plus actual views/walking/model joins remain required; geometry is not beauty acceptance'}
    raw['manifest.json']=encoded(manifest)
    if sum(map(len,raw.values()))>MAX_OUTPUT:raise UserError('Neighborhood artwork exceeds finite allocation')
    output.mkdir(parents=True,exist_ok=False)
    for name,value in raw.items():(output/name).write_bytes(value)
    return {'output':str(output),'buildings':20,'checks':checks,'files':manifest['files']}


def prepare(home,artwork,registry_path,cottage_survey_path,craft_survey_path,exclusion_paths,output,checkpoint_id,checkpoint_sha):
    """Exact saved before/delta/full inputs; never native commands or BE replay."""
    home,artwork,output=(Path(value).resolve() for value in (home,artwork,output))
    if (output.exists() or not output.is_relative_to(home/'staging') or len(exclusion_paths)!=3
            or not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))):
        raise UserError('New private artistic-world binding directory and original exclusions required')
    reserve=guard(4*MIB,MAX_OUTPUT)
    checkpoint=read_json(home/'dashboard/settlement/backup-receipt.json')
    if checkpoint.get('verified') is not True or checkpoint.get('id')!=checkpoint_id or checkpoint.get('sha256')!=checkpoint_sha:
        raise UserError('Exact current verified stopped checkpoint required')
    registry=read_json(registry_path)
    exclusions=[(name,read_json(path),digest(Path(path))) for name,path in zip(('cottage','bascule','rosebridge'),exclusion_paths)]
    districts=construct(registry,read_json(cottage_survey_path),read_json(craft_survey_path),exclusions)
    checks=check(districts);inputs={};world_targets={}
    for name,d in districts.items():
        geometry_path=artwork/(name+'-geometry.json');full_path=artwork/(name+'-full-verification-UNBOUND.json')
        if digest(geometry_path)!=ARTWORK[name][0] or digest(full_path)!=ARTWORK[name][1]:
            raise UserError('Frozen neighborhood artwork differs: '+name)
        geometry,full=read_json(geometry_path),read_json(full_path)
        if full['seed']!=registry['seed'] or full['world_path']!=registry['world_path']:
            raise UserError('Neighborhood artwork belongs to another world')
        changed={pos:state for pos,state in d.p.blocks.items() if state!=d.base.blocks.get(pos,AIR)}
        if geometry['changes']!=[[*pos,state] for pos,state in sorted(changed.items())]:
            raise UserError('Pure source geometry drifted from frozen artwork')
        expected={tuple(pos[i]+d.p.origin[i] for i in range(3)):state for pos,state in d.p.blocks.items()}
        if flatten(full)!=expected:raise UserError('Full artwork geometry is not the complete pure composition')
        for pos in changed:
            world=tuple(pos[i]+d.p.origin[i] for i in range(3))
            if world in world_targets:raise UserError('Two neighborhood depth districts overlap')
            world_targets[world]=(name,pos,d.base.blocks.get(pos,AIR))
        inputs[name]=(d,changed,full)
    snapshot=BackupWorld(home,checkpoint,registry);actual={}
    try:
        for world,(name,pos,expected) in world_targets.items():
            state=snapshot.state(world)
            if base(state)!=base(expected) or any(properties(state).get(k)!=v for k,v in properties(expected).items()):
                raise UserError('Saved neighborhood preimage differs; preserve actual state: '+str((name,world,expected,state)))
            actual[world]=state
        if any(world in snapshot.protected for world in world_targets):
            raise UserError('A neighborhood target is an actual saved BE, including default/unwritten contents')
        sources=list(snapshot.sources)
    finally:snapshot.close()
    raw={};details={}
    for name,(d,changed,full) in inputs.items():
        world_changed={tuple(pos[i]+d.p.origin[i] for i in range(3)):state for pos,state in changed.items()}
        before={world:actual[world] for world in world_changed}
        old=payload(full,before,checkpoint_sha,name+' exact current before: VERIFY ONLY')
        old.update(verification_only=True,construction_forbidden=True)
        delta=payload(full,world_changed,checkpoint_sha,name+' architectural depth DELTA ONLY')
        delta.pop('verification_only',None);delta.pop('construction_forbidden',None)
        delta.update(validation='Fresh native before zero differences; parent-owned empty-server delta placement and strict after verification required',block_entities=[])
        after=copy.deepcopy(full);after.update(backup_sha256=checkpoint_sha,verification_only=True,construction_forbidden=True)
        rollback=copy.deepcopy(old);rollback['name']=name+' exact before RECOVERY ONLY - separate review/admission required'
        for suffix,doc in (('before',old),('delta',delta),('full-verification',after),('rollback',rollback)):
            raw[name+'-'+suffix+'.json']=encoded(doc)
        details[name]={'targets':len(changed),'buildings':d.effects,'checks':checks[name],
                       'actual_saved_BEs_targeted_or_replayed':0,'original_exclusions':getattr(d.base,'mask_provenance',[])}
    if len(world_targets)!=1287:raise UserError('Exact reviewed1287-target artwork required')
    manifest={'format':'awft-neighborhood-depth-current-admission:1','source_sha256':digest(Path(__file__)),
              'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'world_targets':len(world_targets),
              'buildings':20,'districts':details,'saved_sources':sources,'native_actions':False,'reserve_guard':reserve,
              'files':{name:{'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()} for name,value in raw.items()},
              'gate':'Each exact native before must pass; place only that district delta, then native settle/strict full verification and actual graphical/walking review; never place full/before/rollback files'}
    raw['manifest.json']=encoded(manifest)
    if sum(map(len,raw.values()))>MAX_OUTPUT:raise UserError('Neighborhood binding exceeds finite allocation')
    output.mkdir(parents=True,exist_ok=False)
    for name,value in raw.items():(output/name).write_bytes(value)
    return {'output':str(output),'world_targets':len(world_targets),'buildings':20,'files':manifest['files']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('home','registry-path','cottage-survey-path','craft-survey-path','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--exclusion-paths',type=Path,nargs=3,required=True)
    print(json.dumps(author(**vars(parser.parse_args())),indent=2))
