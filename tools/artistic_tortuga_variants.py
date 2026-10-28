"""Native-state-correct orthogonal variants of the original Tortuga recipes.

Pure authored geometry only. All stair/door/bed/beam directions and actual
window/ridge joins are transformed; appearance, survival and use need native
views. This does not move, copy or rename any real-world inventory/entity.
"""
from __future__ import annotations
from copy import deepcopy
from tools.artistic_tortuga_frontages import RECIPES,check,key
from tools.artistic_west_r2_frontage import canonical_joins
from tools.artistic_spawn_plaza import state
from tools.settlement_attractions import properties
from control_room.common import UserError

FACES=('north','east','south','west')


def rotated_state(registry,value,turn):
    if turn not in(0,1,2,3):raise UserError('An explicit orthogonal authored turn is required')
    name=key(value);out={};definition=registry['blocks'][name]
    for prop,choice in properties(value).items():
        dest=FACES[(FACES.index(prop)+turn)%4]if prop in FACES else prop
        if prop in('axis_x','axis_z')and turn%2:dest='axis_z'if prop=='axis_x'else'axis_x'
        if prop in('facing','horizontal_facing')and choice in FACES:
            # Native resizable plank windows have a plane, not four faces.
            if set(definition[prop])=={'north','east'}:choice=FACES[(FACES.index(choice)+turn)%2]
            else:choice=FACES[(FACES.index(choice)+turn)%4]
        if prop=='axis'and choice in('x','z')and turn%2:choice='z'if choice=='x'else'x'
        if prop=='rotation'and set(definition[prop])=={str(n)for n in range(16)}:choice=str((int(choice)+4*turn)%16)
        out[dest]=choice
    return state(registry,name,**out)


def variant(registry,recipe,turn=0,*,name=None,trade=None,trim_sky=True):
    if recipe not in RECIPES:raise UserError('Exact original recipe required')
    return variant_of(RECIPES[recipe](registry),recipe,turn,name=name,trade=trade,trim_sky=trim_sky)


def variant_of(p,recipe,turn=0,*,name=None,trade=None,trim_sky=True):
    """Transform a separately source-bound, fresh pure recipe; never a save."""
    if turn not in(0,1,2,3):raise UserError('An explicit orthogonal authored turn is required')
    registry=p.registry;check(p);original_owner=p.owner;owner=name or original_owner
    def yaw(x,z):return((x,z),(-z,x),(-x,-z),(z,-x))[turn]
    main=[yaw(x,z)for x,z in p.main[original_owner]];min_x=min(x for x,z in main);min_z=min(z for x,z in main)
    def point(q):
        x,z=yaw(q[0],q[2]);return x-min_x,q[1],z-min_z
    def cells(field):return{(yaw(x,z)[0]-min_x,yaw(x,z)[1]-min_z)for x,z in field}
    original_roofs=deepcopy(p.roof_sections)
    p.blocks={point(q):rotated_state(registry,v,turn)for q,v in p.blocks.items()}
    p.tags={point(q):v for q,v in p.tags.items()};p.owners={point(q):owner for q in p.owners}
    p.main={owner:cells(p.main[original_owner])};p.levels={owner:[cells(v)for v in p.levels[original_owner]]}
    p.floors={(owner,y):cells(v)for(old_owner,y),v in p.floors.items()}
    for r in p.routes:r.update(owner=owner,positions=[list(point(q))for q in r['positions']])
    for r in p.props:r.update(owner=owner,position=list(point(r['position'])))
    for r in p.rooms:r.update(owner=owner,standing_point=list(point(r['standing_point'])))
    for r in p.supports:r.update(detail=list(point(r['detail'])),support=list(point(r['support'])))
    for r in p.entries:
        r.update(owner=owner,door=list(point(r['door'])),outside_step=list(point(r['outside_step'])),outward=FACES[(FACES.index(r['outward'])+turn)%4])
    for r in p.roof_sections:
        x0,z0,x1,z1=r['bounds_xz'];corners=[yaw(x,z)for x,z in((x0,z0),(x1,z0),(x0,z1),(x1,z1))]
        r.update(owner=owner,bounds_xz=[min(x for x,z in corners)-min_x,min(z for x,z in corners)-min_z,max(x for x,z in corners)-min_x,max(z for x,z in corners)-min_z],
                 original_profile_rotation_turns=turn,profile_axis='z'if turn%2 else'x')
        if turn in(2,3):r['cross_profile']=list(reversed(r['cross_profile']))
    p.owner=owner;p.features={owner:[f'Original {recipe} individually composed at {turn} quarter turns','Actual occupied volume, stairs, furniture and full native face/axis transforms retained']}
    p.variant_provenance={'original_recipe':recipe,'original_owner':original_owner,'turn_quarters':turn,'original_main_normalization':[min_x,min_z],'original_roof_sections':original_roofs}
    if name:
        for q in list(p.tags):
            if key(p.blocks[q]).endswith('_wall_sign'):
                face=properties(p.blocks[q])['facing'];p.sign(*q,face,[name,trade or'Home • Working Trade'])
    if trim_sky:
        # Original single prototypes clear a tall bounding volume. A new
        # dense composition needs its real rooms/headroom, not an invented
        # empty sky reservation above every low annex. Omit only AIR above
        # the local highest solid; keep all named route/room two-high cells.
        required={tuple((q[0],q[1]+h,q[2]))for r in p.routes for q in r['positions']for h in(0,1)}
        required|={tuple((r['standing_point'][0],r['standing_point'][1]+h,r['standing_point'][2]))for r in p.rooms for h in(0,1)}
        tops={}
        for(x,y,z),value in p.blocks.items():
            if value!='minecraft:air':tops[x,z]=max(tops.get((x,z),-100),y)
        dropped=[]
        for q,value in list(p.blocks.items()):
            if value=='minecraft:air'and q not in required and q[1]>tops.get((q[0],q[2]),-100)+1:
                p.blocks.pop(q);p.owners.pop(q,None);dropped.append(q)
        p.variant_provenance['unneeded_sky_AIR_omitted']=len(dropped)
        p.variant_provenance['named_internal_routes_and_room_clearance_retained']=True
    canonical_joins(p);check(p)
    return p
