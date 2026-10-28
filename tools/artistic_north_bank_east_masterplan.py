"""Measured eastern town composition beyond frozen Rose Reach.

Finite authored plot programs and actual one-metre dry-outline evidence only.
This is not an executable house/placement generator, acceptance score or a grid
of cloned shells. First-quarter native views inform the subsequent 3D artwork.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_north_bank_east import EastPlan,Lot,ROSE_REACH,qualify_lot,outline
from tools.playtest import guard

MIB=1024**2

@dataclass(frozen=True)
class Intent:
    ident:str
    name:str
    use:str
    center:tuple
    size:tuple
    stories:int
    face:str
    shape:str
    roof:str
    motif:str

COMPASS_BEND=(
 Intent('seabird-ledger','The Seabird Ledger','Customs clerk household',(1237,-1207),(9,9),2,'south','cropped_sw','saltbox','A stone-footed corner study, recessed front door and a modest sea-facing kitchen loggia'),
 Intent('three-kestrels','Three Kestrels House','Crew family home',(1251,-1205),(9,11),3,'south','recess_ne','gambrel','Three unequal upper window bays, a tucked-back washing court and domestic gallery above the family hearth'),
 Intent('brass-finch','The Brass Finch','Watch and clock repair',(1266,-1207),(9,9),3,'south','cropped_ne','steep','Narrow carved clock gable, lit instrument window, work bench and little upper writing-room bay'),
 Intent('anchor-apple','Anchor & Apple','Produce and provisions',(1281,-1206),(9,11),2,'south','recess_sw','half_hip','A sheltered recessed produce counter with baskets, bay-window kitchen and a short outward stair'),
 Intent('ink-tern','Ink & Tern','Scribe and household',(1296,-1207),(9,11),3,'south','cropped_nw','cross_gable','An angled ink-shop corner, paired reading windows, fine ceiling grids and an inhabited roof desk'),
 Intent('reed-resonance','Reed & Resonance','Music and instrument repair',(1312,-1207),(9,11),2,'south','recess_se','gambrel','A deep music window, asymmetrical sound-board loft, pinned tools and a separate family supper corner'),
 Intent('rosemary-court','The Rosemary Court','Gardener household',(1328,-1206),(9,11),2,'south','cropped_nw','saltbox','A contoured low garden court, half-sheltered potting ledge and a high-light kitchen window'),
 Intent('salt-wind','The Salt-Wind House','Waterfront household',(1350,-1207),(9,11),3,'west','cropped_ne','steep','A coastal cut-corner footprint, small vertical sea bay and distinct stepped rear stair return'),
)

TIDEFOLD=(
 Intent('pippins-net','Pippin’s Net','Mariner household',(1239,-1187),(9,11),2,'north','recess_nw','half_hip','A supported shallow veranda, working net table and flowering upper side window'),
 Intent('marigold-steps','Marigold Steps','Extended family home',(1254,-1186),(9,11),3,'north','cropped_sw','cross_gable','Two displaced roof peaks, an off-centre inner stair and a sheltered doorstep conversation seat'),
 Intent('blue-quilt','The Blue Quilt','Seamstress household',(1269,-1186),(9,11),3,'north','recess_ne','gambrel','A three-part cloth window, little rear washing court and deeply framed bedroom openings'),
 Intent('copper-window','Copper Window House','Metal trader household',(1285,-1186),(9,11),2,'north','cropped_se','saltbox','An asymmetric copper-edged bay, pantry steps and an airy upper reading alcove'),
 Intent('juniper-son','Juniper & Son','Toy carver and household',(1301,-1186),(9,11),2,'north','recess_sw','cross_gable','A carved toyshop corner, hand-tool wall, workroom side porch and family table above'),
 Intent('azure-key','The Azure Key','Retired navigator home',(1317,-1186),(9,11),3,'north','cropped_ne','steep','A narrow chart-room gable, supported upper balcony and side-wall chimney recess'),
 Intent('roseate-corner','Roseate Corner','Three-generation household',(1333,-1187),(9,11),3,'north','recess_se','gambrel','A diagonal-looking chamfered entrance, bent upper jetty and low pottery-lined front sill'),
 Intent('long-tide','The Long Tide','Marine glass repair',(1350,-1185),(9,11),2,'west','cropped_sw','half_hip','A low sea-view roof with a taller workshop dormer, glazed display bay and a recess for glass stock'),
)

LANTERN_FOLD=(
 Intent('fernhook','Fernhook','Compact household',(1240,-1166),(7,11),2,'east','cropped_nw','saltbox','A narrow hooked-corner house with a raised side bench and a surprisingly generous rear kitchen'),
 Intent('willow-button','The Willow Button','Dressmaker household',(1255,-1165),(9,11),3,'south','recess_sw','gambrel','A scalloped cloth-window composition, small sewing gallery and planted domestic stair landing'),
 Intent('orchard-key','Orchard Key House','Herbalist household',(1271,-1165),(9,11),3,'south','cropped_ne','cross_gable','An inhabited herb library, projecting garden window and a tiny protected porch instead of a wide canopy'),
 Intent('moth-candle','The Moth & Candle','Candlemaker workshop',(1287,-1166),(9,11),2,'south','recess_nw','half_hip','A wax-workbench display, intimate lamp counter and a high-light sitting room under the hip'),
 Intent('honeysuckle-fold','Honeysuckle Fold','Weaver household',(1303,-1166),(9,11),3,'south','cropped_se','gambrel','A folded street corner, long loom window, linen shelves and a split-front family loft'),
 Intent('starlings-rest','Starling’s Rest','Cargo accountant household',(1319,-1166),(9,11),3,'south','recess_ne','cross_gable','A little ledger desk behind a real projecting bay, two different gables and a warm shared supper room'),
 Intent('greycap-terrace','Greycap Terrace','Retired harbor workers home',(1335,-1166),(9,11),2,'south','cropped_sw','saltbox','A low sheltered front terrace, chess/tea nook and carved window corners facing the street bend'),
 Intent('lantern-watch','The Lantern Watch','Waterfront lookout household',(1352,-1165),(7,11),3,'west','cropped_se','steep','A very narrow visible lantern gable and inhabited lookout room, not an empty monumental watchtower'),
)

EAST_HOOK=(
 Intent('driftglass','Driftglass','Potter household',(1262,-1144),(7,11),2,'north','cropped_sw','gambrel','A narrow kiln-free pottery home with a cut doorstep, small display niche and roof-level bedroom window'),
 Intent('sea-lavender','The Sea Lavender','Flower collector household',(1277,-1144),(9,11),3,'north','recess_ne','cross_gable','Contained flowers and a framed glass bay, a small book corner and airy upper sleeping rooms'),
 Intent('amberwake','Amberwake','Sailor household',(1293,-1144),(9,11),2,'north','cropped_nw','half_hip','A weathered low hip, half-recessed entry seat and built-in sea-chest story corners'),
 Intent('turnstone','Turnstone House','Extended family household',(1309,-1144),(9,11),3,'north','recess_sw','cross_gable','Two offset roof crests, an articulated three-generation kitchen and connected little upper rooms'),
 Intent('masons-hearth','Mason’s Hearth','Stoneworker household',(1323,-1144),(9,11),2,'north','cropped_ne','saltbox','A broad recessed stone window, carved but modest porch and a warm protected reading hearth'),
 Intent('east-hook','The East Hook','Compact captain household',(1357,-1142),(7,11),2,'west','cropped_se','steep','A slim final shore gable, tiny sea-facing gallery and an off-axis entrance protected from the wind'),
)

GROUPS={'Compass Bend':COMPASS_BEND,'Tidefold':TIDEFOLD,'Lantern Fold':LANTERN_FOLD,'East Hook':EAST_HOOK}


def as_outline(row):
    return Lot(row.ident,row.name,row.use,row.center,row.size,row.stories,row.face,row.shape,row.roof,
               ('minecraft:bricks',)*row.stories,tuple('UNAUTHORED - '+row.use for _ in range(row.stories)),row.motif)


def compose(registry,fine):
    p=EastPlan(registry,fine);occupied={};qualified=[];refused=[]
    # These footprints belong to the already frozen first visual quarter.
    for lot in ROSE_REACH:
        cells,proof=qualify_lot(p,lot)
        for q in cells:occupied[q]=lot.ident
        qualified.append({'id':lot.ident,'name':lot.name,'quarter':'Rose Reach','status':'FULL3D SOURCE PROTOTYPE - actual native/art review pending','main_cells_xz':[list(q) for q in sorted(cells)],'dry_proof':proof})
    for group,rows in GROUPS.items():
        for row in rows:
            lot=as_outline(row)
            try:
                cells,proof=qualify_lot(p,lot)
                if any(q in occupied for q in cells):raise UserError('A proposed original plot overlaps another main outline')
                for q in cells:occupied[q]=row.ident
                qualified.append({'id':row.ident,'name':row.name,'quarter':group,'use':row.use,'stories':row.stories,'front':row.face,'motif':row.motif,'proposed_roof':row.roof,'status':'EXACT saved dry main/skirt outline only - unique3D artwork/interiors NOT yet authored','main_cells_xz':[list(q) for q in sorted(cells)],'dry_proof':proof})
            except UserError as error:
                refused.append({'id':row.ident,'name':row.name,'quarter':group,'original_center_xz':list(row.center),'reason':str(error),'status':'REFUSED candidate retained - no geometry/growth/placement authority'})
    return {'quarters':list(GROUPS),'qualified':qualified,'refused':refused,'main_footprint_columns':len(occupied),'source_3D_buildings':7,
            'scope':'Masterplan only. Refusals remain refused; no source/runtime test can turn unbuilt plots into finished houses.'}


def prepare(home,fine_path,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();fine_path=Path(fine_path).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()) or not fine_path.is_relative_to(home/'staging'):raise UserError('Owned private masterplan evidence only')
    reserve=guard(2*MIB,8*MIB);receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or receipt.get('id')!=checkpoint_id or receipt.get('sha256')!=checkpoint_sha:raise UserError('Exact current stopped source checkpoint required')
    if fine_path.stat().st_size>16*MIB:raise UserError('Finite measured eastern field required')
    fine=read_json(fine_path)
    if fine.get('checkpoint_sha256')!=checkpoint_sha:raise UserError('Saved geography must match the stopped checkpoint')
    data=compose(read_json(home/'dashboard/settlement/registry.json'),fine);data.update(format='awft-authored-east-masterplan:1',checkpoint_id=checkpoint_id,checkpoint_sha256=checkpoint_sha,
            fine_land_sha256=digest(fine_path),source_sha256=digest(Path(__file__)),reserve=reserve,native_actions=0,world_writes=0,
            preserved={'accepted_street_harbor_and_taverns':True,'working_bridge_river_navigation':True,'western_Castle_lane':'X<=1216; separate original shops/source','eastern_scope':'X>=1217; each exact dry outline, never water rectangles','zipline_v2':'Western station/13frames/curve corridor is Grand-owned and untouched; oldv1 superseded'})
    raw=(json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode()
    if len(raw)>8*MIB:raise UserError('Finite original plot-program evidence exceeded')
    out=home/'staging'/('north-bank-eastern-masterplan-'+str(time.time_ns()));out.mkdir();(out/'masterplan.json').write_bytes(raw)
    return {'folder':str(out),'sha256':hashlib.sha256(raw).hexdigest(),'qualified_plots':len(data['qualified']),'refused_plots':data['refused'],'modeled_buildings':7,'world_actions':0}
