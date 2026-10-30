"""Closed, joined eastern roof volumes and genuinely articulated end faces.

Original block geometry only. No game, world, inventory or native calls.
"""
from __future__ import annotations

from tools.artistic_captains_hall import VEC
from tools.artistic_west_r2_frontage import key

AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}
PANELS=('minecraft:gray_terracotta','minecraft:brown_terracotta','minecraft:light_gray_terracotta')


def roof_surface(box,base,kind,axis):
    """Both opposite pitches are present; an end hip only clips their ends."""
    x0,z0,x1,z1=box;surface={};peak=(x1-x0)//2 if axis=='x'else(z1-z0)//2
    for x in range(x0,x1+1):
        for z in range(z0,z1+1):
            a=min(x-x0,x1-x)if axis=='x'else min(z-z0,z1-z)
            b=min(z-z0,z1-z)if axis=='x'else min(x-x0,x1-x)
            rise=min(a,b)if kind=='hip'else min(a,b+2)if kind=='halfhip'else a
            if rise==a:
                face=('east'if x<(x0+x1)/2 else'west')if axis=='x'else('south'if z<(z0+z1)/2 else'north')
            else:face=('south'if z<(z0+z1)/2 else'north')if axis=='x'else('east'if x<(x0+x1)/2 else'west')
            ridge=a==peak and rise==a
            if kind=='hip'and a==b:ridge=True
            surface[x,z]={'y':base+rise,'facing':face,'ridge':ridge,'dormer':False}
    return surface


def dormer_surfaces(surface,box,base,axis,variant):
    """Union a small transverse roof volume into the main roof, never atop it."""
    x0,z0,x1,z1=box;across=x1-x0 if axis=='x'else z1-z0;along=z1-z0 if axis=='x'else x1-x0
    if across<10 or along<12:return []
    positions=[(along//3,1)]
    if along>=18:positions.append((2*along//3,-1))
    result=[]
    for n,(offset,sign)in enumerate(positions):
        sign=sign if variant%2==0 else-sign
        center=(z0 if axis=='x'else x0)+max(3,min(along-3,offset))
        front=(x0+1 if sign==1 else x1-1)if axis=='x'else(z0+1 if sign==1 else z1-1)
        columns=set();walls={}
        for depth in range(-1,6):
            across_q=front+sign*depth
            if not((x0<=across_q<=x1)if axis=='x'else(z0<=across_q<=z1)):continue
            for c in range(center-2,center+3):
                q=(across_q,c)if axis=='x'else(c,across_q)
                if q not in surface:continue
                old=surface[q]['y'];y=base+3+min(c-(center-2),center+2-c)
                if y<=old:continue
                surface[q]={'y':y,'facing':('south'if c<center else'north')if axis=='x'else('east'if c<center else'west'),
                    'ridge':c==center,'dormer':True}
                columns.add(q)
                if depth>=0 and(c in(center-1,center+1)or depth==0):
                    walls[q]=(old,y)
        if columns:result.append({'axis':axis,'front':front,'center':center,'inward_sign':sign,'columns':columns,'walls':walls,'base':base,'kind':'transverse closed dormer with real front glazing'})
    return result


def _blocked(p,q):
    return(q in p.fixed or q in p.body or q in getattr(p,'backing_points',set())or q in getattr(p,'route_floor_points',set())
        or q in getattr(p,'entry_clearance_points',set())or q in getattr(p,'entry_door_states',{}))


def _higher_room(p,q,base):
    x,y,z=q
    for cells,low,top in zip(getattr(p,'mass_fields',[]),getattr(p,'mass_floors',[]),getattr(p,'top_levels',[])):
        if top>base and(x,z)in cells and low<y<=top:return True
    return False


def _put(p,q,material,*,base=None,**props):
    if _blocked(p,q)or(base is not None and _higher_room(p,q,base)):return False
    return p.put(*q,material,**props)


def _timber(p,q,axis,role,*,base=None):
    material={'x':'chipped:reinforced_dark_oak_log','z':'chipped:edged_stripped_dark_oak_log','y':'minecraft:stripped_dark_oak_log'}[axis]
    return _put(p,q,material,axis=axis,role=role,base=base)


def _end_glazing(p,wall,base,axis,face,surface):
    """Glazing sits in a thick framed end; shutters project from real cheeks."""
    x0,z0,x1,z1=wall;center=(x0+x1)//2 if axis=='x'else(z0+z1)//2
    candidates=[]
    for c in(center-1,center):
        x,z=(c,z0)if axis=='x'else(x0,c)
        if surface.get((x,z),{}).get('y',base)<=base+2:continue
        candidates.append((x,z))
    if not candidates:return
    points=[(x,base+h,z)for x,z in candidates for h in(1,2)]
    if any(_blocked(p,q)or _higher_room(p,q,base)for q in points):return
    for q in points:_put(p,q,'mcwwindows:dark_oak_four_window',facing=face,windowstate='locked',role='real recessed glazed attic end between solid timber cheeks',base=base)
    dx,dz=VEC[face];tx,tz=(1,0)if dz else(0,1)
    left=candidates[0];right=candidates[-1]
    for side,(x,z)in enumerate(((left[0]-tx,left[1]-tz),(right[0]+tx,right[1]+tz))):
        for h in(1,2):
            back=x,base+h,z;outside=x+dx,base+h,z+dz
            if key(p.blocks.get(back,'minecraft:air'))not in AIR and key(p.blocks.get(outside,'minecraft:air'))in AIR:
                _put(p,outside,'mcwwindows:dark_oak_louvered_shutter',facing=face,hinge='left'if side==0 else'right',open=True,role='actual open louvered attic shutter rooted at solid gable cheek',base=base)


def compose_roof(p,box,base,intent,*,force_kind=None,force_axis=None,family=None):
    x0,z0,x1,z1=box;axis=force_axis or('x'if x1-x0<=z1-z0 else'z')
    kind=force_kind or('halfhip'if'halfhip'in intent else'gable'if'dark'in intent or'cross-gabled'in intent else'hip')
    family=family or('dark_oak'if'dark'in intent else'spruce'if'halfhip'in intent else'gray_terracotta'if'cross-gabled'in intent else'brown_terracotta')
    surface=roof_surface(box,base,kind,axis)
    dormers=dormer_surfaces(surface,box,base,axis,p.index)
    # Fascia is tied laterally to the structural wall one block inward. Different
    # true corner caps separate the crossing horizontal beams structurally.
    for x in range(x0,x1+1):
        for z in range(z0,z1+1):
            if x not in(x0,x1)and z not in(z0,z1):continue
            q=x,base-1,z
            if x in(x0,x1)and z in(z0,z1):_put(p,q,'minecraft:dark_oak_wood',axis='y',role='actual corner cap joining two rooted eave fascia beams',base=base)
            else:_timber(p,q,'x'if z in(z0,z1)else'z','closed roof eave beam attached to the mass ceiling edge',base=base)
    # Closed gable/half-hip ends, all the way down to the real ceiling/floor tie.
    end_faces=('north','south')if axis=='x'else('west','east')
    for face in end_faces:
        coords=[(x,z0+1 if face=='north'else z1-1)for x in range(x0+1,x1)]if axis=='x'else[(x0+1 if face=='west'else x1-1,z)for z in range(z0+1,z1)]
        for x,z in coords:
            for y in range(base,surface[x,z]['y']):
                c=x-x0 if axis=='x'else z-z0
                if c%4==0:_timber(p,(x,y,z),'y','actual upright gable stud dividing broad infill panels',base=base)
                elif y==base or(y-base)%3==0:_timber(p,(x,y,z),axis,'deep gable cross tie supporting the closed roof end',base=base)
                else:_put(p,(x,y,z),PANELS[p.index%3],role='full three-dimensional framed gable closure',base=base)
    for dormer in dormers:
        for(x,z),(low,high)in dormer['walls'].items():
            for y in range(low,high):
                c=z if axis=='x'else x
                depth=abs((x if axis=='x'else z)-dormer['front'])
                if c!=dormer['center']and depth%4==0:_timber(p,(x,y,z),'y','actual separated dormer corner stud',base=base)
                elif y==base+3:_timber(p,(x,y,z),'z'if axis=='x'else'x','closed dormer window lintel and side tie',base=base)
                else:_put(p,(x,y,z),PANELS[p.index%3],role='real dormer front closure below its transverse roof',base=base)
        x,z=(dormer['front'],dormer['center'])if axis=='x'else(dormer['center'],dormer['front'])
        face=('west'if dormer['inward_sign']==1 else'east')if axis=='x'else('north'if dormer['inward_sign']==1 else'south')
        for y in(base+1,base+2):_put(p,(x,y,z),'mcwwindows:dark_oak_four_window',facing=face,windowstate='locked',role='two-high actual dormer window opening into the closed roof volume',base=base)
    # Emit the UNION roof skin once. A transverse dormer replaces hidden main
    # facets instead of leaving disconnected second sheets hovering over them.
    for(x,z),r in sorted(surface.items()):
        y=r['y'];q=x,y,z
        cross_x=r['facing']in('east','west')
        if r['ridge']:
            ridge_axis=('x'if axis=='x'else'z')if r['dormer']else('z'if axis=='x'else'x')
            _put(p,q,'minecraft:'+('dark_oak'if ridge_axis=='z'else'spruce')+'_slab',type='bottom',waterlogged=False,role='closed continuous ridge where the two actual pitches meet',base=base)
        elif cross_x:_put(p,q,'mcwroofs:'+family+'_roof',facing=r['facing'],half='bottom',shape='straight',role='opposed long roof facet, joined to its other pitch',base=base)
        else:
            end={'dark_oak':'dark_oak','spruce':'spruce','gray_terracotta':'deepslate_brick','brown_terracotta':'mud_brick'}[family]
            _put(p,q,'minecraft:'+end+'_stairs',facing=r['facing'],half='bottom',shape='straight',waterlogged=False,role='actual orthogonal hip or cross-gable facet of the same quiet roof family',base=base)
        below=x,y-1,z
        if y>base and key(p.blocks.get(below,'minecraft:air'))in AIR:_put(p,below,'minecraft:'+('dark_oak'if cross_x else'spruce')+'_slab',type='top',waterlogged=False,role='top-half underside rafter touching the actual roof skin',base=base)
    for face in end_faces:
        wall=(x0+1,z0+1,x1-1,z0+1)if face=='north'else(x0+1,z1-1,x1-1,z1-1)if face=='south'else(x0+1,z0+1,x0+1,z1-1)if face=='west'else(x1-1,z0+1,x1-1,z1-1)
        _end_glazing(p,wall,base,axis,face,surface)
    if not hasattr(p,'roof_volume_details'):p.roof_volume_details=[]
    p.roof_volume_details.append({'box':list(box),'base':base,'axis':axis,'kind':kind,'opposite_pitches':True,
        'ridge_closed':True,'eave_overhang_blocks':1,'dormers':[{'front':r['front'],'center':r['center'],'kind':r['kind']}for r in dormers]})
    return ('closed '+kind+' '+family+' roof, opposed pitches, framed ends and '+str(len(dormers))+' integrated glazed dormers')


def articulate_endwalls(p,box,levels,*,axis):
    """Upper windows use actual exposed height, never just a ground footprint."""
    x0,z0,x1,z1=box;faces=('north','south','west','east');made=[]
    for face in faces:
        dx,dz=VEC[face];tx,tz=(1,0)if dz else(0,1)
        horizontal=bool(dz);span=(x1-x0)if horizontal else(z1-z0)
        centers=[span//2]if span<11 else list(range(3,span-2,5))
        for floor,level in enumerate(levels):
            y=level+1
            for c in centers:
                x,z=(x0+c,z0 if face=='north'else z1)if horizontal else(x0 if face=='west'else x1,z0+c)
                points=[(x+n*tx,y+h,z+n*tz)for n in(0,1)for h in(0,1)]
                outside=[(a+dx,b,d+dz)for a,b,d in points]
                # A split-level mass can contain an interior lower zone that
                # never reaches this facade. It does not create another row
                # of windows across the higher exterior wall.
                declared=getattr(p,'declared',None)
                if declared is not None and any(level not in declared.get((a,d),[])for a,_,d in points):continue
                cheeks=[(x+n*tx,y+h,z+n*tz)for n in(-1,2)for h in(0,1)]
                # Keep a real timber jamb between already authored casements.
                # Filling the two-cell gap can join three separate windows
                # into one six-cell glass band on both perpendicular faces.
                if any(_blocked(p,q)or key(p.blocks.get(q,'minecraft:air')).startswith('mcwwindows:')for q in cheeks):continue
                if any(_blocked(p,q)or not p.permitted(q)for q in points+outside):continue
                if any((q[0],q[2])in p.other_columns for q in outside):continue
                if any(key(p.blocks.get(q,'minecraft:air'))not in AIR for q in outside):continue
                allowed=lambda v:key(v)in PANELS or key(v).startswith('mcwwindows:')or(key(v).startswith('chipped:')and key(v).endswith(('_log','_planks')))or key(v)in('minecraft:dark_oak_wood','minecraft:stripped_dark_oak_log')
                if any(not allowed(p.blocks.get(q,'minecraft:air'))for q in points):continue
                for q in points:_put(p,q,'mcwwindows:dark_oak_four_window',facing=face,windowstate='locked',role='real deeply framed exposed endwall casement')
                for q in cheeks:
                    if allowed(p.blocks.get(q,'minecraft:air')):_timber(p,q,'y','solid timber casement jamb separating neighbouring panes')
                # All low circulation stays empty. Projection begins above
                # normal head height; upper bays gain literal sill and knees.
                for n in(-1,0,1,2):_timber(p,(x+n*tx+dx,y+2,z+n*tz+dz),'x'if tx else'z','actual projecting endwall casement cornice')
                if floor>0:
                    for n in(0,1):
                        _put(p,(x+n*tx+dx,level,z+n*tz+dz),'minecraft:dark_oak_slab',type='top',waterlogged=False,role='upper endwall bay sill attached to the real floor band')
                    for n in(-1,2):
                        back=x+n*tx,level-1,z+n*tz
                        q=back[0]+dx,back[1],back[2]+dz
                        if key(p.blocks.get(back,'minecraft:air'))not in AIR:_put(p,q,'mythrais:curved_corbel_dark_oak',facing=face,shape=0,role='rooted carved upper casement knee, above ground walking headroom')
                    for n,hinge in((-1,'left'),(2,'right')):
                        for h in(0,1):
                            back=x+n*tx,y+h,z+n*tz;q=back[0]+dx,back[1],back[2]+dz
                            if key(p.blocks.get(back,'minecraft:air'))not in AIR:_put(p,q,'mcwwindows:dark_oak_louvered_shutter',facing=face,hinge=hinge,open=True,role='actual projecting weathered louvered shutter at a solid upper wall cheek')
                made.append({'face':face,'window':[x,y,z],'floor':level,'genuine_glazing_and_projection':True})
    return made
