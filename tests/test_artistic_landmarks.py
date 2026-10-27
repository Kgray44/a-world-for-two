"""Geometry regressions; native registry and graphical review are separate gates."""
import unittest
from collections import deque

from control_room.common import UserError
from tools.artistic_landmarks import AIR, Prototype, bridge_deck, construct, payload, prepare, refine_bridge_bank, rotate_state, rotate_xz, world_cameras, world_point


class Properties(dict):
    def __contains__(self, key):return True
    def __getitem__(self, key):
        return ['true','false','none','low','high','north','south','east','west','x','y','z',
                'bottom','top','straight','top_end_0','base','above','closed','lower','upper',
                'left','right','single','pink','brown','flower','foot','head',
                'calcite','floor','middle','tray','white','yellow','base_wave',
                'bot_l','bot_m','bot_r','mid_l','mid_m','mid_r','top_l','top_m','top_r']+[str(n) for n in range(17)]


class Palette(dict):
    def __contains__(self, key):return True
    def __getitem__(self, key):return Properties()


class LandmarkGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry={'blocks':Palette(),'seed':0,'world_path':'staging/fixture/world'}
        cls.castle=construct(cls.registry,'castle-gatehouse')
        cls.palace=construct(cls.registry,'castle-palace')
        cls.bridge=construct(cls.registry,'rosebridge')

    def test_material_rule_includes_all_authored_floors_roofs_and_piers(self):
        for prototype in (self.castle,self.palace,self.bridge):self.assertEqual(prototype.material_violations,[])
        # Display-context removal must retain the planted courtyard soil.
        self.assertNotIn((20,68,-16),self.castle.terrain)
        self.assertEqual(self.castle.blocks[20,68,-16],'minecraft:dirt')

    def test_approach_gate_and_bridge_routes_have_two_clear_blocks(self):
        for prototype in (self.castle,self.bridge):
            for route in prototype.routes:
                x,y,z=route['point']
                for dy in (0,1):self.assertEqual(prototype.blocks.get((x,y+dy,z),AIR),AIR,(route,dy))
                self.assertNotEqual(prototype.blocks.get((x,y-1,z),AIR),AIR,route)
        self.assertIn('stairs',self.castle.blocks[0,68,20])
        self.assertIn('stairs',self.castle.blocks[0,64,46])

    def test_native_door_halves_and_raised_court_foundations_survive(self):
        for y in (69,79):
            self.assertIn('half=lower',self.castle.blocks[-15,y,1])
            self.assertIn('half=upper',self.castle.blocks[-15,y+1,1])
        for x,z in ((0,0),(-25,-10),(20,-10),(0,12)):
            for y in range(64,68):self.assertNotEqual(self.castle.blocks.get((x,y,z),AIR),AIR)
        self.assertTrue(any(r['name']=='West tower chart lookout' and r['floor']==88 for r in self.castle.rooms))

    def test_arches_are_open_and_contain_no_habitable_room_or_inventory(self):
        self.assertEqual(self.bridge.rooms,[])
        for center in (-32,0,32):
            for x in range(-4,5):
                for y in range(64,68):self.assertEqual(self.bridge.blocks.get((x,y,center)),AIR)
        self.assertFalse(any('door' in s or 'barrel' in s or 'chest' in s or 'bed[' in s for s in self.bridge.blocks.values()))
        self.assertEqual(bridge_deck(0),74)
        self.assertEqual(bridge_deck(49),69)
        # Actual junction image exposed daylight below raised top-slab caps.
        for x in (-5,5):
            for z in (-44,-28,-12,12,28,44):
                self.assertIn('type=bottom',self.bridge.blocks[x,bridge_deck(z)+3,z])

    def test_bank_terrace_refuses_wet_corners_and_protected_native_ground(self):
        def survey():
            return {'samples':[{'x':x,'z':z,'fluid':False,'ground_y':64,'block_entities':[]}
                               for x in range(1292,1317,4) for z in range(-1120,-1103,4)]}
        profile=survey();p=construct(self.registry,'rosebridge')
        admission=refine_bridge_bank(p,profile,(1248,-1104),1,90)
        self.assertEqual(admission['additional_habitable_rooms'],0)
        self.assertEqual(admission['moving_or_mechanical_changes'],0)
        self.assertEqual(p.blocks[-5,65,-58],AIR)
        self.assertNotEqual(p.blocks[-5,64,-58],AIR)
        profile=survey()
        next(s for s in profile['samples'] if (s['x'],s['z'])==(1300,-1112))['fluid']=True
        with self.assertRaises(UserError):refine_bridge_bank(construct(self.registry,'rosebridge'),profile,(1248,-1104),1,90)
        profile=survey();profile['samples'][0]['block_entities']=[[1305,64,-1115]]
        with self.assertRaises(UserError):refine_bridge_bank(construct(self.registry,'rosebridge'),profile,(1248,-1104),1,90)

    def test_actual_review_roof_gap_and_empty_gallery_have_structural_repairs(self):
        # View8 showed daylight through this whole annulus in r1. It must now
        # be full stone, not an outer top-slab trim standing above a short wall.
        for x,z in ((-16,0),(-7,0),(-11,-5),(-11,4)):
            state=self.castle.blocks[x,92,z]
            self.assertNotEqual(state,AIR);self.assertNotIn('slab',state)
        # The formerly blank library has real tall bookcase banks and a lit
        # fireplace; the projecting window bay is actually accessible.
        for y in range(79,84):self.assertEqual(self.castle.blocks[-25,y,-10],'minecraft:bookshelf')
        self.assertIn('dawnoftimebuilder:limestone_fireplace',self.castle.blocks[-30,79,-4])
        self.assertIn('mcwdoors:cherry_classic_door',self.castle.blocks[0,79,5])
        self.assertEqual(self.castle.blocks[-22,79,5],AIR)

    def test_payload_context_is_explicit_and_origin_is_translated(self):
        value=payload(self.castle,self.registry,'a'*64,(1214,-1008),4)
        self.assertEqual(value['commands'],[])
        self.assertEqual(value['block_entities'],[])
        self.assertEqual(value['backup_sha256'],'a'*64)
        self.assertLess(len(value['blocks']),len(self.castle.blocks))
        self.assertTrue(any(row[:3]==[1214,72,-1008] for row in value['blocks']))
        full=payload(self.castle,self.registry,'a'*64,include_context=True)
        self.assertEqual(len(full['blocks']),len(self.castle.blocks))

    def test_palace_room_routes_do_not_stop_at_decorative_sills_or_upper_floors(self):
        # This discrete source check permits operable doors and thin carpets;
        # it is not native collision-shape or player traversal acceptance.
        blocks=self.palace.blocks
        def material(q):return blocks.get(q,AIR).split('[',1)[0]
        def clear(q):
            s=material(q)
            return s in (AIR,'minecraft:vine') or s.endswith(('_carpet','_curtain','_door'))
        def walkable(q):
            x,y,z=q
            return clear(q) and clear((x,y+1,z)) and material((x,y-1,z)) not in (AIR,'minecraft:water')
        todo=deque([(20,69,-14)]);reached=set(todo)
        while todo:
            x,y,z=todo.popleft()
            for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
                for dy in (0,1,-1):
                    q=x+dx,y+dy,z+dz
                    if q in reached or not(-43<=q[0]<=77 and -39<=q[2]<=25 and 64<=q[1]<=100):continue
                    if not walkable(q) or (dy==1 and not clear((x,y+2,z))):continue
                    reached.add(q);todo.append(q)
        for destination in ((38,69,-15),(52,69,-22),(50,79,-24),(50,89,-23),
                            (50,99,-22),(50,69,3),(52,79,-12),(44,79,4),
                            (64,69,-20),(26,79,-27),(41,79,-28),(70,65,-17),
                            (52,89,-35),(52,69,-35),(-36,65,14)):
            self.assertIn(destination,reached,destination)
        # Actual source defects found in review: a projecting window sill
        # blocked this doorway and a reversed fill left the balcony obstructed.
        self.assertEqual(blocks[41,80,-28],AIR)
        self.assertEqual(blocks[52,90,-34],AIR)

    def test_palace_viewing_gallery_and_royal_balcony_have_open_edge_guards(self):
        for x,z in [(x,z) for x in range(46,64) for z in (-6,11)]+[(x,z) for x in (45,64) for z in range(-5,11)]:
            self.assertNotEqual(self.palace.blocks.get((x,79,z),AIR),AIR,(x,z))
        for x in (48,56):
            for z in (-35,-34):self.assertIn('railing_',self.palace.blocks[x,89,z])

    def test_actual_palace_review_roof_intrusions_and_blind_glazing_are_repaired(self):
        # Native r1 image5 showed a green guest roof through this royal floor;
        # image6 showed the music bay's back gable hanging into the ballroom.
        for x in (43,44):
            for z in range(-28,-24):self.assertNotIn('prismarine',self.palace.blocks.get((x,89,z),AIR))
        for x in range(49,56):
            for y in range(79,88):
                for z in (12,13):self.assertNotIn('prismarine',self.palace.blocks.get((x,y,z),AIR))
        self.assertTrue(self.palace.blocks[42,73,2].startswith('mcwwindows:quartz_window'))
        self.assertTrue(self.palace.blocks[71,73,-31].startswith('mcwwindows:diorite_window'))
        self.assertEqual(self.palace.blocks[75,73,-30],AIR)
        self.assertEqual(self.palace.blocks[41,60,3],self.palace.masonry(41,60,3))

    def test_final_room_detail_keeps_window_reveals_dance_floor_and_native_seats(self):
        # The lower guest wall also occluded the hall's glazing in real r2.
        for x in (43,44,45):self.assertEqual(self.palace.blocks[x,73,-26],AIR)
        for x in range(50,61):
            for z in range(-1,9):
                for y in (69,70):self.assertEqual(self.palace.blocks.get((x,y,z),AIR),AIR)
        for x in (49,54):self.assertTrue(self.palace.blocks[x,70,-30].startswith('handcrafted:cherry_chair'))
        self.assertTrue(self.palace.blocks[73,70,-26].startswith('handcrafted:berry_jam_jar'))
        self.assertTrue(self.palace.blocks[73,69,-26].startswith('handcrafted:dark_oak_counter'))
        self.assertNotEqual(self.palace.blocks[77,89,-8],AIR)
        for x in (51,52,53):self.assertEqual(self.palace.blocks[x,90,13],AIR)
        for x in (49,59):
            for y in (72,75):self.assertNotEqual(self.palace.blocks[x,y,-8],AIR)

    def test_unknown_palette_and_official_runtime_are_refused(self):
        with self.assertRaises(UserError):Prototype({'blocks':{}},'castle-gatehouse').put(0,64,0,'missing:roof')
        with self.assertRaises(UserError):prepare('D:/A World for Two','castle-gatehouse')

    def test_east_west_bridge_turn_rotates_state_keys_and_actual_camera(self):
        self.assertEqual(rotate_xz(0,-48,90),(48,0))
        stair='minecraft:stone_brick_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]'
        self.assertIn('facing=east',rotate_state(self.bridge,stair,90))
        wall='minecraft:stone_brick_wall[east=none,north=low,south=low,up=false,waterlogged=false,west=none]'
        turned=rotate_state(self.bridge,wall,90)
        self.assertIn('east=low',turned);self.assertIn('west=low',turned)
        self.assertIn('north=none',turned);self.assertIn('south=none',turned)
        self.assertIn('axis=z',rotate_state(self.bridge,'minecraft:oak_log[axis=x]',90))
        restored=stair
        for _ in range(4):restored=rotate_state(self.bridge,restored,90)
        self.assertEqual(restored,stair)
        camera=next(c for c in world_cameras(self.bridge,(1248,-1104),1,90) if c['name']=='Road approach')
        self.assertEqual(camera['position'],[1200,72,-1104]);self.assertEqual(camera['look_at'],[1248,77,-1104])
        self.assertAlmostEqual(camera['yaw'],-90)
        value=payload(self.bridge,self.registry,'a'*64,(1248,-1104),1,rotation=90)
        native={tuple(row[:3]):value['palette'][row[3]] for row in value['blocks']}
        for route in self.bridge.routes:
            x,y,z=world_point(route['point'],(1248,-1104),1,90)
            self.assertNotEqual(native.get((x,y-1,z),AIR),AIR)
            self.assertEqual(native.get((x,y,z),AIR),AIR)


if __name__=='__main__':unittest.main()
