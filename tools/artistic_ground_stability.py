"""Finite literal gravity-substrate qualification for saved coastal footings.

A gravel-looking dry surface above another gravel block is insufficient. Stop
at the FIRST non-gravity state: water, AIR, unknown or an unqualified material
refuses the column. This never searches across a gap or fills below a building.
"""
from __future__ import annotations

GRAVITY={'minecraft:gravel','minecraft:sand','minecraft:red_sand'}
# Pinned vanilla non-falling natural substrate families only. Modded blocks and
# arbitrary manmade solids need separate native qualification, not guesswork.
STABLE_NATURAL={
    'minecraft:stone','minecraft:granite','minecraft:diorite','minecraft:andesite',
    'minecraft:deepslate','minecraft:tuff','minecraft:dirt','minecraft:grass_block',
    'minecraft:coarse_dirt','minecraft:rooted_dirt','minecraft:podzol','minecraft:mycelium',
    'minecraft:sandstone','minecraft:red_sandstone','minecraft:clay','minecraft:mud',
    'minecraft:packed_mud','minecraft:terracotta','minecraft:calcite','minecraft:bedrock',
    *('minecraft:'+prefix+ore+'_ore'for prefix in('','deepslate_')for ore in('coal','iron','copper','gold','redstone','lapis','diamond','emerald')),
}


def natural_mount(lookup,x,z,*,top=62,bottom=-64):
    if type(top)is not int or type(bottom)is not int or not(-64<=bottom<=top<=63)or top-bottom>127:
        raise ValueError('Finite saved footing range required')
    stack=[]
    for y in range(top,bottom-1,-1):
        state=lookup(x,y,z);stack.append((x,y,z,state));name=(state or'UNKNOWN').split('[',1)[0]
        if name in GRAVITY and'waterlogged=true'not in state:continue
        stable=name in STABLE_NATURAL and'waterlogged=true'not in state if state is not None else False
        return {'stable':stable,'stack':stack,'first_non_gravity':stack[-1],
                'gravity_cells':len(stack)-1,'reason':'literal qualified non-falling native substrate'if stable else'first non-gravity state is AIR, water, unknown or unqualified; no crossing/fill'}
    return {'stable':False,'stack':stack,'gravity_cells':len(stack),'reason':'finite substrate bound reached; no assumption below it'}
