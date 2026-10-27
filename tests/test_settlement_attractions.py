import copy
import hashlib
import json
import math
import struct
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from control_room.common import Layout, UserError
from tools.settlement_attractions import (
    AIR, BOUNDS, AttractionPlan, BackupWorld, NBTReader, construct, payload,
    prepare, properties, unpack_section, validate_systems,
)


def fixture():
    axis={'axis':['x','y','z']};wet={'waterlogged':['false','true']}
    cardinal=['north','south','east','west'];all_faces=cardinal+['up','down']
    blocks={'minecraft:'+key:{} for key in (
        'air','stone','dirt','grass_block','stone_bricks','spruce_planks','calcite',
        'glass','bricks','dark_oak_planks','potted_pink_tulip')}
    blocks.update({'minecraft:stripped_spruce_log':axis,
        'minecraft:spruce_fence':{},'minecraft:water':{'level':[str(n) for n in range(16)]},
        'minecraft:chest':{'facing':cardinal,'type':['single','left','right'],**wet},
        'minecraft:hopper':{'facing':all_faces,'enabled':['true','false']},
        'minecraft:lever':{'face':['floor','wall','ceiling'],'facing':cardinal,'powered':['true','false']},
        'minecraft:oak_sign':{'rotation':[str(n) for n in range(16)],**wet},
        'minecraft:oak_door':{'facing':cardinal,'half':['lower','upper'],'hinge':['left','right'],
                              'open':['true','false'],'powered':['true','false']},
        'minecraft:lantern':{'hanging':['true','false'],**wet},
        'minecraft:ladder':{'facing':cardinal,**wet},
        'minecraft:spruce_trapdoor':{'facing':cardinal,'half':['top','bottom'],
            'open':['true','false'],'powered':['true','false'],**wet}})
    for key in ('dark_prismarine_stairs','spruce_stairs'):
        blocks['minecraft:'+key]={'facing':cardinal,'half':['bottom','top'],'shape':['straight'],**wet}
    for key in ('dark_prismarine_slab','stone_brick_slab'):
        blocks['minecraft:'+key]={'type':['bottom','top','double'],**wet}
    blocks.update({'create:'+key:{**axis,**wet} for key in ('shaft','cogwheel','large_cogwheel')})
    blocks.update({'create:clutch':{**axis,'powered':['false','true']},
        'create:gearbox':axis,'create:andesite_encased_shaft':axis,
        'create:water_wheel':{'facing':all_faces},'create:millstone':{},
        'create:mechanical_press':{'facing':cardinal},'create:depot':wet,
        'create:chute':{'facing':all_faces,'shape':['normal'],**wet},
        'create:controls':{'facing':cardinal,'open':['true','false'],'virtual':['true','false'],**wet},
        'create:small_bogey':{'axis':['x','z'],**wet},'create:blue_seat':wet,
        'handcrafted:spruce_bench':{'facing':cardinal,'color':['blue'],
            'shape':['left','middle','right'],**wet},
        'create:track_station':{'assembling':['true','false'],**wet},
        'railways:track_spruce':{'shape':['zo'],'turn':['true','false'],**wet},
        'overpressure:item_pump':{'facing':all_faces,**wet},
        'overpressure:pneumatic_connection':{'facing':all_faces,'arrow_facing':cardinal,
            'mode':['extract','insert','disabled'],'powered':['true','false']},
        'overpressure:pneumatic_tube':{**{k:['true','false'] for k in all_faces},**wet},
        'create_hypertube:hypertube':{**{k:['true','false'] for k in ('connected','east_west','north_south','up_down')},**wet},
        'create_hypertube:hypertube_entrance':{'facing':all_faces,
            **{k:['true','false'] for k in ('locked','powered','open','has_block_in_front')},**wet}})
    return SimpleNamespace(registry={'blocks':blocks,'seed':'42','world_path':'synthetic-world',
        'items':['minecraft:wheat','minecraft:iron_ingot','create:wrench','create:super_glue','create:schedule']},
        backup={'verified':True,'id':'20261027T034106Z-ecd64f','sha256':'a'*64},
        previous={},protected=set(),headroom=set(),immutable=set(),sources=[])


class SurfaceWorld:
    def __init__(self):
        self.protected=set();self.sources=[];self.chunks={};self.override={}

    def state(self,pos):
        return self.override.get(tuple(pos),AIR if pos[1]>66 else 'minecraft:grass_block' if pos[1]==66 else 'minecraft:stone')

    def close(self):
        pass


def nbt(kind,value):
    if kind in (1,3,4):
        return struct.pack('>'+{1:'b',3:'i',4:'q'}[kind],value)
    if kind==8:
        raw=value.encode();return struct.pack('>H',len(raw))+raw
    if kind in (11,12):
        return struct.pack('>i',len(value))+struct.pack('>'+str(len(value))+('i' if kind==11 else 'q'),*value)
    if kind==9:
        child,rows=value
        return bytes([child])+struct.pack('>i',len(rows))+b''.join(nbt(child,row) for row in rows)
    if kind==10:
        return b''.join(bytes([child])+nbt(8,name)+nbt(child,row) for name,(child,row) in value.items())+b'\0'
    raise AssertionError(kind)


def root(value):
    return b'\x0a\0\0'+nbt(10,value)


def saved_fixture(home):
    home=Path(home);backup=home/'backups';backup.mkdir()
    level=zlib.compress(root({'Data':(10,{'DataVersion':(3,3955),
        'WorldGenSettings':(10,{'seed':(4,42)})})}),wbits=31)
    chunk=root({'xPos':(3,80),'zPos':(3,-63),'Status':(8,'minecraft:full'),
        'sections':(9,(10,[{'Y':(1,4),'block_states':(10,{
            'palette':(9,(10,[{'Name':(8,'minecraft:stone')},{'Name':(8,AIR)}])),
            'data':(12,[0]*256)})}])),
        'block_entities':(9,(10,[{'x':(3,1292),'y':(3,67),'z':(3,-1000)}]))})
    compressed=zlib.compress(chunk);content=struct.pack('>I',len(compressed)+1)+b'\x02'+compressed
    region=bytearray(12288);slot=(((-63)&31)*32+(80&31))*4
    region[slot:slot+4]=(2*256+1).to_bytes(4,'big');region[8192:8192+len(content)]=content
    rows={'world/AWorldForTwo/level.dat':level,'world/AWorldForTwo/region/r.2.-2.mca':bytes(region)}
    name='20261027T034106Z-ecd64f';file=backup/(name+'.zip')
    with zipfile.ZipFile(file,'x') as archive:
        for path,raw in rows.items():archive.writestr(path,raw)
        archive.writestr('awft-backup.json',json.dumps({'format':1,'files':[
            {'path':path,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for path,raw in rows.items()]}))
    sha=hashlib.sha256(file.read_bytes()).hexdigest()
    file.with_suffix('.json').write_text(json.dumps({'integrity':'verified','sha256':sha}))
    return {'id':name,'verified':True,'sha256':sha},{'world_path':str(home/'world/AWorldForTwo'),'seed':'42'}


class SavedPreimageTests(unittest.TestCase):
    def test_modern_five_bit_palette_values_do_not_cross_long_padding(self):
        palette=[{'Name':'test:block_'+str(n)} for n in range(17)]
        values=[0]*math.ceil(4096/12)
        values[0]=16<<55;values[1]=9
        section={'block_states':{'palette':palette,'data':values}}
        self.assertEqual(unpack_section(section,11,0,0),'test:block_16')
        self.assertEqual(unpack_section(section,12,0,0),'test:block_9')
        section['block_states']['data'].pop()
        with self.assertRaises(UserError):unpack_section(section,0,0,0)

    def test_named_nbt_truncation_and_unbounded_lists_are_rejected(self):
        self.assertEqual(NBTReader(root({'value':(8,'hello')})).read()['value'],'hello')
        for raw in (b'\x0a\0',root({})+b'junk',b'\x0a\0\0\x09\0\x01x\x0a\x7f\xff\xff\xff'):
            with self.assertRaises(UserError):NBTReader(raw).read()

    def test_backup_reads_exact_authenticated_saved_states_without_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt,registry=saved_fixture(tmp);before=set(Path(tmp).rglob('*'))
            world=BackupWorld(tmp,receipt,registry)
            try:
                self.assertEqual(world.state((1292,67,-1000)),'minecraft:stone')
                self.assertIn((1292,67,-1000),world.protected)
                self.assertEqual(world.state((1292,82,-1000)),AIR)
                with self.assertRaisesRegex(UserError,'no generated chunk'):world.state((1316,67,-1000))
            finally:world.close()
            self.assertEqual(set(Path(tmp).rglob('*')),before)

    def test_changed_zip_or_other_saved_seed_cannot_supply_preconditions(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt,registry=saved_fixture(tmp)
            with self.assertRaisesRegex(UserError,'digest'):BackupWorld(tmp,dict(receipt,sha256='0'*64),registry)
            with self.assertRaisesRegex(UserError,'not the registry world'):BackupWorld(tmp,receipt,dict(registry,seed='43'))


class AttractionContractTests(unittest.TestCase):
    def setUp(self):
        self.ctx=fixture();self.snapshot=SurfaceWorld();self.plan=construct(self.ctx,self.snapshot)

    def test_complementary_mechanisms_and_independent_player_routes(self):
        proof=validate_systems(self.plan)
        self.assertEqual((proof['hypertube_route_extent_blocks'],proof['track_blocks'],proof['bogeys']),(61,103,2))
        self.assertEqual((proof['entrance_minimum_rpm'],proof['entrance_drive_ratio']),(16,2))
        self.assertEqual(self.plan.systems['hypertube']['native_span_lengths'],[30,30])
        self.assertEqual(proof['hypertube_native_anchor_blocks'],3)
        self.assertEqual(set(self.plan.systems),{'watermill','pneumatic','hypertube','railway'})
        self.assertEqual(self.plan.systems['railway']['station_distance_blocks'],82)
        self.assertEqual(abs(-995//16-(-935//16)),4)
        self.assertTrue(all(BOUNDS[0]<=x<=BOUNDS[2] and BOUNDS[1]<=z<=BOUNDS[3] for x,y,z in self.plan.blocks))

    def test_a_broken_drivetrain_or_pneumatic_elbow_cannot_pass_preflight(self):
        for pos in ((1302,71,-1002),(1300,72,-1002),(1297,72,-1008)):
            plan=copy.copy(self.plan);plan.blocks=dict(self.plan.blocks);plan.blocks[pos]=AIR
            with self.assertRaises(UserError):validate_systems(plan)
        plan=copy.copy(self.plan);plan.blocks=dict(self.plan.blocks)
        plan.blocks[(1297,72,-1002)]='overpressure:pneumatic_tube[east=true,west=true]'
        with self.assertRaisesRegex(UserError,'branch points'):validate_systems(plan)

    def test_hydraulic_seal_and_stopped_empty_inputs_are_real_requirements(self):
        self.assertIn('powered=true',self.plan.blocks[(1297,71,-1002)])
        self.assertEqual(self.plan.blocks[(1296,71,-1002)],'create:andesite_encased_shaft[axis=x]')
        for pos in ((1292,70,-1002),(1296,71,-1002)):
            plan=copy.copy(self.plan);plan.blocks=dict(self.plan.blocks);plan.blocks[pos]=AIR
            with self.assertRaises(UserError):validate_systems(plan)
        plan=copy.copy(self.plan);plan.tags=dict(self.plan.tags)
        plan.tags[(1302,75,-1002)]='{Items:[{id:"minecraft:wheat",count:16}]}'
        with self.assertRaisesRegex(UserError,'start empty'):validate_systems(plan)
        self.assertIn('count:16',self.plan.tags[(1303,69,-1008)])

    def test_player_tube_egress_and_rail_axis_cannot_be_faked(self):
        for pos,state in (((1311,69,-960),'minecraft:stone'),
                          ((1311,66,-1001),AIR),
                          ((1316,70,-1004),'create:small_bogey[axis=x]'),
                          ((1313,72,-1004),'minecraft:stone')):
            plan=copy.copy(self.plan);plan.blocks=dict(self.plan.blocks);plan.blocks[pos]=state
            with self.assertRaises(UserError):validate_systems(plan)
        for station in self.plan.systems['railway']['stations']:
            tag=self.plan.tags[tuple(station['position'])]
            self.assertIn('TargetTrack:[I;4,-2,0]',tag)
            self.assertNotIn('Facing',tag)

    def test_completed_air_routes_entities_and_new_saved_structures_are_fixed(self):
        pos=(1300,70,-1002)
        for collection in ('previous','protected','headroom','immutable'):
            ctx=fixture()
            if collection=='previous':ctx.previous[pos]=AIR
            else:getattr(ctx,collection).add(pos)
            plan=AttractionPlan(ctx,SurfaceWorld())
            with self.assertRaisesRegex(UserError,'construction/access'):plan.put(*pos,'minecraft:stone')
        for state in ('minecraft:chest','minecraft:spruce_planks'):
            world=SurfaceWorld();world.override[pos]=state;plan=AttractionPlan(fixture(),world)
            with self.assertRaises(UserError):plan.put(*pos,AIR)
        world=SurfaceWorld();world.protected.add(pos);plan=AttractionPlan(fixture(),world)
        with self.assertRaises(UserError):plan.put(*pos,AIR)

    def test_native_properties_and_current_plan_never_silently_change(self):
        for key,props in (('minecraft:stone',{'facing':'east'}),('create:track_station',{'facing':'east'})):
            with self.assertRaises(UserError):self.plan.state(key,**props)
        with self.assertRaises(UserError):self.plan.put(1291,69,-1000,AIR)
        document=payload(self.plan,self.plan.blocks,'synthetic','synthetic',tags=True)
        self.assertEqual(document['commands'],[])
        self.assertEqual(len(document['block_entities']),14)

    def test_prepare_writes_only_unique_private_bundle_with_complete_preconditions(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);target=Layout(home).state/'settlement/owned-attractions'
            with patch('tools.settlement_attractions.load',return_value=self.ctx),\
                 patch('tools.settlement_attractions.BackupWorld',return_value=self.snapshot),\
                 patch('tools.settlement_attractions.Storage.reserve'):
                result=prepare(home,target)
                manifest=json.loads(Path(result['manifest']).read_text())
                before=json.loads((target/manifest['preconditions_file']).read_text())
                self.assertEqual(len(before['blocks']),len(self.plan.blocks))
                self.assertEqual(len(manifest['expected_previous']),len(self.plan.blocks))
                self.assertFalse((Layout(home).state/'settlement/plan.json').exists())
                self.assertEqual(manifest['commands'],0)
                with self.assertRaisesRegex(UserError,'fresh private'):prepare(home,target)
                with self.assertRaisesRegex(UserError,'fresh private'):prepare(home,home/'outside')


if __name__=='__main__':
    unittest.main()
