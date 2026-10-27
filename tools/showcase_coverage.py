"""Audit showcase coverage from pinned JAR identities and archived native receipts.

This is a read-only world audit. Collection reads cached files, never connects to
Minecraft, and writes only a bounded, sanitized private input snapshot. Rendering
that snapshot produces the public catalogue and report reproducibly. A block or
an item in a chest is deliberately not a gameplay acceptance receipt.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tomllib
import zipfile

from control_room.common import REPO, UserError, atomic_write, digest, read_json


FORMAT = 'awft-showcase-inputs:1'
REPORT_FORMAT = 'awft-showcase-coverage:1'
MAX_INPUT = 16 * 1024**2
MAX_PLAN = 32 * 1024**2
MAX_JAR = 128 * 1024**2
GUARD = Path(r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1')
ID = re.compile(r'^[a-z0-9_.-]+:[a-z0-9_./-]+$')
MOD_ID = re.compile(r'^[a-z][a-z0-9_]*$')
SHA = re.compile(r'^[0-9a-f]{64}$')
SOURCE_LABELS = (
    'Original village and homestead', 'Lanternwater pirate port',
    'Grand River Drawbridge architecture', 'Rosewater Castle', 'South-bank district',
    'The Rosewater Resolute', 'The Amberwake', "The Nightingale's Debt", 'The Sea Lavender',
    'Grand harbor quays and tenders',
)
FIXED_RECEIPTS = (
    'core-verification-pass.json', 'pirate-port-verification-pass.json',
    'drawbridge-block-verification.json',
    'rosewater-castle-67f1bd76c75e-verify.json',
    'south-bank-08b57f748987-verify-shared-read.json',
    'ship-rosewater-resolute-c612729b69ef-verify.json',
    'ship-amberwake-f3fdaea349ea-verify.json',
    'ship-nightingales-debt-8552b39eca0f-verify.json',
    'ship-sea-lavender-3d7129b42b6d-verify.json',
    'grand-harbor-access-e31b6d478228-verify.json',
)
# Only these declared children are feature namespaces of their root bundle.
# An arbitrary assets/ folder, project slug or bundled API is not namespace proof.
BUNDLE_NAMESPACES = {'aeronautics_bundled': ('aeronautics', 'offroad', 'simulated')}
LIBRARIES = set('''almanac architectury athena balm bluelib blueprint caelus cloth_config
commonnetworking creativecore cristellib curios create_dragons_plus emberstextapi
fzzy_config geckolib glitchcore gottschcore hapi konkrete melody moonlight owo
player_animation_library playeranimator puzzleslib resourcefulconfig resourcefullib
ritchiesprojectilelib searchables shetiphiancore sophisticatedcore sparkweave
supermartijn642configlib supermartijn642corelib blockui yungsapi
moogs_structures lithostitched yet_another_config_lib_v3'''.split())
PERFORMANCE = set('''clumps dynamic_fps entityculling ferritecore immediatelyfast
letmedespawn lithium modernfix moreculling sodium'''.split())
WORLD_GENERATION = set('''ancientstructures archaeology_ruins mr_aztec_ruins castleshift
castles_and_keeps mr_epic_structuresjungletemples gianttree mtr philipsruins
regions_unexplored tectonic terralith t_and_t dungeons_arise woven_in_time
betterdeserttemples betterjungletemples betteroceanmonuments'''.split())
BACKGROUND = {
    'chunky': 'Optional operator-controlled generation tool; no decorative proxy. Check bounded generation, cancellation and idle tickets separately.',
    'spark': 'Diagnostics tool; a profiling capture and correct interpretation demonstrate it, not a placed block.',
    'paxi': 'Loads the pinned data/resource configuration. Check actual reload and resource provenance, not a model exhibit.',
    'awft_control_bridge': 'Control Room integration and native server operations; exact drawbridge behavior is separately scoped below.',
    'squaremap': 'Browser renderer; check actual map tiles, dimensions, updates and player markers independently of handmade map decorations.',
    'openpartiesandclaims': 'Two-account party, protection and teammate checks are required; avoid forced-loading claims for a display.',
    'sttn': 'Sleep behavior requires players and a real night transition; a bed alone is insufficient.',
}
GOALS = {
    'advancedweather': 'Observe actual local atmospheric weather and use a real weather instrument/station; record its output without forcing destructive weather over protected builds.',
    'amendments': 'Use its supported functional furnishing interactions, including the actual modded behavior rather than a vanilla lookalike.',
    'animalgarden_sugarglider': 'Observe a real sugar glider habitat and its normal movement/interaction; a cage label is insufficient.',
    'aquaculture': 'Fish with the mod gear, identify a mod fish and use the resulting catch; item stocks alone are insufficient.',
    'armoroftheages': 'Equip a displayed historical armor set and check its visual fit and normal equipment behavior.',
    'bdd': 'Observe the selected dragon content without disturbing the protected home; record actual interaction and persistence.',
    'bettercombat': 'Try the actual weapon animation and attack timing with a safe target; a weapon rack is insufficient.',
    'buildinggadgets2': 'Build, undo and restore a bounded sample with the real gadget and its resource rules.',
    'carryon': 'Pick up and safely replace a permitted block/entity with contents and ownership intact.',
    'chipped': 'Use the real workbench to convert a material and compare several appropriate variants in a named building.',
    'cinematic': 'Use supported vanilla crafting/furnace stations and confirm the scene exits cleanly; table presence alone is insufficient.',
    'comforts': 'Use a sleeping bag/hammock and check spawn-point behavior and shared sleep rules.',
    'constructionwand': 'Extend and undo a small wall with the actual wand and correct material consumption.',
    'tombstone': 'Exercise a disposable death/recovery route, gravestone access and item return without risking player equipment.',
    'cozys_improved_cats': 'Meet a real cat, verify its intended appearance/behavior, and test pet ownership without static NoAI substitutes.',
    'create': 'Operate the real drawbridge, then commission processing, logistics and passenger transport separately; decorative shafts are insufficient.',
    'sablexaeromaps': 'Track a real moving Aeronautics/Sable contraption on Xaero maps, including turn and chunk boundary.',
    'aeronautics_bundled': 'Assemble and pilot a bounded real airship, dock it, and check movement/return/restart; historic static sailing hulls do not qualify.',
    'createbigcannons': 'Identify a complete safe unloaded cannon assembly and later test authorized firing away from permanent builds.',
    'createaddition': 'Demonstrate an actual powered conversion or complementary processing chain with visible input/output.',
    'createdeco': 'Inspect the integrated industrial material, lighting and trim palette in a named workshop.',
    'sliceanddice': 'Prepare food with an actual powered kitchen processing chain and verify output.',
    'create_central_kitchen': 'Demonstrate a selected food-processing integration with correct input/output rather than a menu label.',
    'create_hypertube': 'Commission both native Bezier spans and entrance drives, ride both ways, test a chunk crossing and restart.',
    'createornithopterglider': 'Deploy the actual glider, fly/land safely and check durability and multiplayer visibility.',
    'overpressure': 'Power the actual pump and route a counted item batch through the filtered extractor/tubes/inserter; test restart.',
    'create_sophback_compat': 'Check the claimed backpack/Create interaction with the actual selected versions and a controlled item batch.',
    'crittersandcompanions': 'Observe live mod animals in appropriate habitat and verify normal AI/interaction; scenery alone is insufficient.',
    'dawnoftimebuilder': 'Walk through furnished culturally appropriate rooms showing several real block families and accessible stairs/doors.',
    'doggytalents': 'Interact with a real owned dog, check its training/bed and safe owner commands.',
    'domum_ornamentum': 'Craft and apply a material variant using the actual architect cutter, then check material retention.',
    'effortlessbuilding': 'Build and undo a bounded sample with the real placement modes and resource rules.',
    'envelope': 'Write a letter, pack a parcel, and complete actual delivery between two players, including the pigeon delivery feature.',
    'explorerscompass': 'Search a real generated structure, travel there and verify the result; a compass in a chest is insufficient.',
    'exposure': 'Take, develop and view an actual photograph from the overlook, including multiplayer sharing.',
    'fairylights': 'Inspect several real connected light runs at night and check connections and switches.',
    'fairytales': 'Meet an actual fairy and demonstrate a wish/blessing/ability safely; a fairy garden or wings display does not qualify.',
    'farmersdelight': 'Prepare a meal at the actual stove/cooking pot/cutting board and verify the food and byproducts.',
    'farm_and_charm': 'Use its actual crop/animal/food loop in a staffed farm and kitchen rather than only decorative crops.',
    'vinery': 'Grow/harvest grapes and use actual wine-making/storage steps; inspect the working vineyard.',
    'fishofthieves': 'Catch and identify a Sea of Thieves fish with the actual fishing loop and check its display/preparation.',
    'framedblocks': 'Build several camouflaged framed shapes, change and recover their materials, and inspect fit in an actual room.',
    'handcrafted': 'Walk furnished rooms and use suitable seats/storage; a lone chair does not establish a complete furnished exhibit.',
    'hybrid_aquatic': 'Visit an actual aquatic habitat and verify living creatures and safe interactions without dense decorative spawning.',
    'icarus': 'Equip real wings, take off and land, and check energy/durability and multiplayer appearance.',
    'icarusrewinged': 'Use the selected Icarus extension and verify its actual wing behavior rather than an item stock.',
    'immersive_melodies': 'Play an actual instrument and verify playback/volume for both players.',
    'jgpg': 'Inspect a flintlock and use a controlled safe target with correct ammunition/reload; never fire at permanent builds.',
    'kaleidoscope_cookery': 'Prepare one of its actual meals with the appropriate workstation and ingredient loop.',
    'lfpirates': 'Meet an actual pirate encounter or settlement away from the home and check normal AI, loot and protection.',
    'lootr': 'Open an actual supported loot container as both players and verify its intended independent loot rules.',
    'mcwbridges': 'Walk the real bridge span and connections, inspecting safe edge protection and headroom.',
    'mcwdoors': 'Use several real door styles in accessible doorways and check fit and operation.',
    'mcwfences': 'Inspect connected real fence/wall styles, corner joins and gates in a named garden.',
    'mcwfurnitures': 'Inspect several actual furniture pieces and exercise usable storage/seat functions where supported.',
    'mcwholidays': 'Inspect a tasteful real seasonal display; a generic vanilla decoration is insufficient.',
    'mcwlights': 'Inspect working real lamps at night and their supported controls.',
    'mcwpaintings': 'Inspect real mod paintings in an accessible gallery; vanilla paintings do not prove this mod.',
    'mcwpaths': 'Walk a connected real path/paving palette linking destinations.',
    'mcwroofs': 'Inspect several real joined roof pieces, slopes and eaves from usable rooms and exterior views.',
    'mcwstairs': 'Walk real stairs and landings with adequate headroom and clean connections.',
    'mcwtrpdoors': 'Use real trapdoors/hatches at safe accessible openings.',
    'mcwwindows': 'Inspect multiple real window families and their fit in furnished rooms.',
    'multibeds': 'Use the actual bed system and verify selected sheets, shared sleep behavior and spawn rules.',
    'music_disc_maker': 'Create and play an actual permitted music disc and verify shared playback and volume.',
    'xercamusic': 'Play an actual instrument/music arrangement and verify synchronized audibility.',
    'mythrais': 'Inspect and use an actual mod equipment choice with its intended combat rules on a safe target.',
    'naturalist': 'Observe live wildlife in an appropriate habitat; normal AI and interaction are separate from entity summoning.',
    'naturescompass': 'Locate and visit a real target biome; a stocked compass is insufficient.',
    'oceansdelight': 'Prepare and eat an actual ocean meal through its intended cooking integration.',
    'polymorph': 'Exercise a real conflicting recipe and choose the intended result without losing materials.',
    'postit': 'Write, place, edit and share an actual note with permissions respected.',
    'rechiseled': 'Use the actual chisel to make multiple connected variants and inspect a coherent room sample.',
    'railways': 'Commission a real Steam n Rails station/carriage and run a passenger trip with safe boarding, return and restart; laid tracks alone are insufficient.',
    'ribbits': 'Visit actual Ribbits content or a suitable live habitat and test its music/trading behavior safely.',
    'sable': 'Demonstrate a bounded actual physics contraption and persistence; a static historical ship is insufficient.',
    'sereneseasons': 'Check the actual seasonal calendar, visible seasonal effects and selected crop behavior.',
    'simplehats': 'Equip real hats and verify appearance for both players.',
    'simplest_scythes': 'Harvest a bounded planted patch with the actual scythe and verify intended area and drops.',
    'simplyswords': 'Use a real weapon on a safe target and verify its actual animation/effect and stats.',
    'smallships': 'Board and sail a real Small Ships entity, use its cargo and two-player seating, return and check restart. Static dockyard hulls and boat items do not qualify.',
    'sophisticatedbackpacks': 'Equip and use an actual backpack with selected upgrades and verify contents survive normal reconnect.',
    'sophisticatedbackpackscreateintegration': 'Exercise its actual Create/backpack transfer interaction without item loss or duplication.',
    'structurize': 'Save, preview and place a bounded structure with the real tools; inspect resource and undo behavior.',
    'supplementaries': 'Use several real utility decorations in context and check their interaction/storage/redstone behavior.',
    'tacz': 'Use an actual selected firearm and ammunition on a controlled safe target, checking reload and multiplayer behavior.',
    'takeaseat': 'Sit and stand from suitable real seating without clipping or movement lock.',
    'treasure2': 'Find and unlock an actual Treasure2 chest through its real key/loot loop; a hand-filled vanilla chest does not qualify.',
    'treasures_of_the_dead': 'Visit an actual pirate/skeleton encounter away from home and verify AI, drops and safe return.',
    'trotting_wagons': 'Hitch an actual horse to a real wagon, drive, brake, use cargo and check reconnect/restart. A parked cart prop is insufficient.',
    'upgrade_aquatic': 'Visit real aquatic content and use a selected feature, maintaining safe habitat and swimming access.',
    'visualworkbench': 'Put items on the actual crafting table and verify in-world display and normal crafting, including Cinematic Interactions.',
    'waystones': 'Activate a real pair and complete balanced player travel with correct cost, ownership and return.',
    'whaleborne': 'Encounter its actual selected ocean content and verify the intended gameplay; a generic ship or treasure prop is insufficient.',
    'yourstruly': 'Draw a real freehand letter, send/share it and hang it in the home with both players able to view it.',
    'zipline': 'Install a real powered/valid endpoint route, ride and brake safely in both directions and check restart. Rope scenery is insufficient.',
}
CLIENT_GOALS = {
    'skinlayers3d': 'Inspect real player skin-layer geometry from several views and verify both players retain the intended skins.',
    'entity_model_features': 'Inspect an actually loaded supported custom entity model/resource pack and confirm normal animation and compatibility.',
    'entity_texture_features': 'Inspect actually loaded supported entity texture features with the intended resource pack and check visual correctness.',
    'ambient_camera': 'Check the actual camera easing/movement features in play and verify responsive controls and normal UI return.',
    'ambientsounds': 'Listen across indoor/outdoor and biome transitions and check actual ambient sound mixing and volume.',
    'controlling': 'Search actual keybinds, identify conflicts and verify typing/selection responsiveness without losing bindings.',
    'fallingleaves': 'Inspect actual foliage particles in a natural scene and check particle density and graphics overhead.',
    'fusion': 'Inspect real connected-texture examples with an actually loaded compatible resource pack; a block palette alone is insufficient.',
    'lambdynlights': 'Carry a light through a dark area and observe actual moving illumination and graphics overhead.',
    'reeses_sodium_options': 'Use the actual Sodium settings interface/search and verify intended settings persist without interfering with Iris.',
    'simplytooltips': 'Inspect actual item/block tooltips and check correctness, readability and input responsiveness.',
    'smoothplayeranimations': 'Observe real player movement and tool-use animation locally and for the other player, checking for visual conflicts.',
    'sound_physics_remastered': 'Compare actual sound propagation/reverb indoors, behind walls and outdoors with comfortable volume and measured overhead.',
    'emotecraft': 'Perform actual emotes and verify synchronized animation and control return for both players.',
    'cinematic_respawn': 'Check the actual death/respawn scene and control return in a disposable safe test.',
    'awft_client_presentation': 'Inspect the real title/menu, original background, button layout and first-join control return.',
    'fancymenu': 'Inspect the actual custom menu, public server-list join flow and suppressed first-run popup.',
    'drippyloadingscreen': 'Inspect the real loading title/subtitle scaling and original background at multiple window sizes.',
    'distanthorizons': 'Inspect actual 128-chunk LOD generation/streaming and graphics under the selected profile.',
    'seedrenderer': 'Verify SeedGen codec/fingerprint and actual distant-terrain output; generated LODs alone do not prove Xaero coverage.',
    'maphorizons': 'Verify the experimental actual SeedGen/DH-to-Xaero terrain integration and mark unsupported behavior honestly.',
    'xaerominimap': 'Verify the actual minimap, death marker, waypoints, player tracking and shared waypoint flow.',
    'xaeroworldmap': 'Verify actual explored terrain, world-map pan/search and waypoint sharing; LOD data is not presumed visible.',
    'iris': 'Inspect actual selected shaders, graphics defects, resource use and switch/restart behavior.',
    'lumiera': 'Play the actual settlement intro and nearby replay scenes and check packet coverage and control return.',
}
PRIORITY = ('envelope', 'framedblocks', 'fairytales', 'naturalist', 'crittersandcompanions',
            'zipline', 'trotting_wagons', 'smallships', 'create_hypertube', 'overpressure',
            'aeronautics_bundled', 'sable', 'treasure2', 'whaleborne', 'createbigcannons',
            'fishofthieves', 'yourstruly')
VANILLA_ANCHORS = {
    'cinematic': {'minecraft:crafting_table', 'minecraft:furnace'},
    'visualworkbench': {'minecraft:crafting_table'},
    'polymorph': {'minecraft:crafting_table'},
    'carryon': {'minecraft:chest', 'minecraft:barrel'},
    'sttn': {'minecraft:'+color+'_bed' for color in
             ('white', 'orange', 'magenta', 'light_blue', 'yellow', 'lime', 'pink', 'gray',
              'light_gray', 'cyan', 'purple', 'blue', 'brown', 'green', 'red', 'black')},
}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def bounded_json(path, limit=MAX_INPUT):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > limit:
        raise UserError('Required bounded audit input is missing or too large: ' + path.name)
    return json.loads(path.read_text('utf-8'))


def reserve(c_bytes, d_bytes):
    """Guard finite writes on both drives; external programs remain outside this rule."""
    if os.name != 'nt':
        return
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                             '-File', str(GUARD), '-EstimatedCBytes', str(c_bytes),
                             '-EstimatedDBytes', str(d_bytes)], capture_output=True,
                            text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        receipt = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise UserError('No usable storage guard receipt') from exc
    if result.returncode or not receipt.get('allowed'):
        raise UserError('Storage reserve rejected the bounded showcase writer')


class SNBT:
    """Bounded reader for authored SNBT, preserving nested item lists accurately.

    This does not validate Minecraft semantics or execute native code. Its only
    purpose is to read explicit item IDs/counts and flags from archived plans;
    unsupported syntax fails closed instead of counting text inside a book.
    """
    def __init__(self, value):
        if not isinstance(value, str) or len(value) > 262144:
            raise UserError('Supplied SNBT exceeded its audit bound')
        self.text, self.i = value, 0

    def ws(self):
        while self.i < len(self.text) and self.text[self.i].isspace():
            self.i += 1

    def quoted(self):
        quote = self.text[self.i]
        self.i += 1
        result = []
        while self.i < len(self.text):
            c = self.text[self.i]
            self.i += 1
            if c == quote:
                return ''.join(result)
            if c == '\\':
                if self.i == len(self.text):
                    break
                c = self.text[self.i]
                self.i += 1
            result.append(c)
        raise UserError('Unterminated supplied SNBT string')

    def value(self, depth=0):
        self.ws()
        if depth > 32 or self.i >= len(self.text):
            raise UserError('Incomplete or excessively nested supplied SNBT')
        c = self.text[self.i]
        if c in ('"', "'"):
            return self.quoted()
        if c == '{':
            self.i += 1
            result = {}
            while True:
                self.ws()
                if self.i < len(self.text) and self.text[self.i] == '}':
                    self.i += 1
                    return result
                if self.i >= len(self.text):
                    break
                if self.text[self.i] in ('"', "'"):
                    key = self.quoted()
                else:
                    start = self.i
                    while self.i < len(self.text) and self.text[self.i] not in ': \t\r\n':
                        self.i += 1
                    key = self.text[start:self.i]
                self.ws()
                if not key or self.i >= len(self.text) or self.text[self.i] != ':':
                    break
                self.i += 1
                if key in result:
                    raise UserError('Duplicate supplied SNBT field')
                result[key] = self.value(depth+1)
                self.ws()
                if self.i < len(self.text) and self.text[self.i] == ',':
                    self.i += 1
                elif self.i >= len(self.text) or self.text[self.i] != '}':
                    break
            raise UserError('Malformed supplied SNBT compound')
        if c == '[':
            self.i += 1
            self.ws()
            if self.text[self.i:self.i+2] in ('I;', 'L;', 'B;'):
                self.i += 2
            result = []
            while True:
                self.ws()
                if self.i < len(self.text) and self.text[self.i] == ']':
                    self.i += 1
                    return result
                result.append(self.value(depth+1))
                self.ws()
                if self.i < len(self.text) and self.text[self.i] == ',':
                    self.i += 1
                elif self.i >= len(self.text) or self.text[self.i] != ']':
                    break
            raise UserError('Malformed supplied SNBT list')
        start = self.i
        while self.i < len(self.text) and self.text[self.i] not in ',]} \t\r\n':
            self.i += 1
        token = self.text[start:self.i]
        if not token:
            raise UserError('Empty supplied SNBT token')
        if re.fullmatch(r'[-+]?\d+[bBsSlL]?', token):
            return int(token.rstrip('bBsSlL'))
        if re.fullmatch(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?[fFdD]?', token):
            return float(token.rstrip('fFdD'))
        return token

    def read(self):
        value = self.value()
        self.ws()
        if self.i != len(self.text) or not isinstance(value, dict):
            raise UserError('Unsupported supplied SNBT remainder/root')
        return value


def read_jar_identity(path, pin):
    """Read exact pinned bytes and bounded native mod declarations, without code execution."""
    path = Path(path)
    if (not path.is_file() or path.stat().st_size != pin['size']
            or path.stat().st_size > MAX_JAR):
        raise UserError('Missing or differently sized pinned mod: ' + pin['filename'])
    algorithm = 'sha512' if pin['hashes'].get('sha512') else 'sha256'
    if not pin['hashes'].get(algorithm) or digest(path, algorithm) != pin['hashes'][algorithm]:
        raise UserError('Pinned mod bytes changed: ' + pin['filename'])
    root, embedded, meta = [], [], []
    mode = None

    def inspect(archive, prefix='', depth=0):
        nonlocal mode
        for name in ('META-INF/neoforge.mods.toml', 'META-INF/mods.toml'):
            if name not in archive.namelist():
                continue
            if archive.getinfo(name).file_size > 1024**2:
                raise UserError('Mod declaration exceeded its metadata bound')
            raw = archive.read(name)
            data = tomllib.loads(raw.decode('utf-8-sig'))
            declared = []
            for row in data.get('mods', []):
                ident = row.get('modId')
                if not isinstance(ident, str) or not MOD_ID.fullmatch(ident):
                    raise UserError('Invalid actual mod ID in pinned JAR')
                declared.append({'id': ident, 'name': str(row.get('displayName', ident)),
                                 'version': str(row.get('version', 'unspecified'))})
            if depth == 0:
                root.extend(declared)
            else:
                embedded.extend({'id': r['id'], 'file': prefix} for r in declared)
            meta.append({'member': prefix + name, 'sha256': sha_bytes(raw)})
            break
        if depth == 0 and 'META-INF/MANIFEST.MF' in archive.namelist():
            if archive.getinfo('META-INF/MANIFEST.MF').file_size > 1024**2:
                raise UserError('Manifest exceeded its metadata bound')
            manifest = archive.read('META-INF/MANIFEST.MF').decode('utf-8', 'replace')
            match = re.search(r'^FMLModType:\s*(\S+)', manifest, re.M)
            mode = match.group(1).upper() if match else None
        if 'META-INF/jarjar/metadata.json' not in archive.namelist() or depth >= 3:
            return
        info = archive.getinfo('META-INF/jarjar/metadata.json')
        if info.file_size > 1024**2:
            raise UserError('Embedded mod declaration exceeded its bound')
        jars = json.loads(archive.read(info.filename)).get('jars', [])
        if len(jars) > 64:
            raise UserError('Too many embedded mod declarations')
        total = 0
        for row in jars:
            child = row.get('path', '')
            if (not isinstance(child, str) or not child.startswith(('META-INF/jarjar/', 'META-INF/jars/'))
                    or not child.endswith('.jar') or '..' in child or '\\' in child):
                raise UserError('Unsafe embedded mod member')
            entry = archive.getinfo(child)
            total += entry.file_size
            if entry.file_size > 32*1024**2 or total > 96*1024**2:
                raise UserError('Embedded mod metadata inspection exceeded its finite bound')
            with zipfile.ZipFile(io.BytesIO(archive.read(child))) as nested:
                inspect(nested, prefix+child+'!/', depth+1)

    with zipfile.ZipFile(path) as archive:
        inspect(archive)
    return {'filename': pin['filename'], 'size': pin['size'], 'hashes': pin['hashes'],
            'declared_mods': sorted(root, key=lambda r: r['id']),
            'embedded_mods': sorted(embedded, key=lambda r: (r['id'], r['file'])),
            'metadata': sorted(meta, key=lambda r: r['member']), 'fml_mod_type': mode}


def source_policy(repo=REPO):
    """Public sanitized evidence supplies the exact archived receipt hashes to recheck."""
    evidence = bounded_json(Path(repo)/'evidence/runtime/settlement-detail-candidate.23.json')
    predecessors = evidence['predecessor_geometry']
    if len(predecessors) != 10:
        raise UserError('All ten completed predecessor sources are required')
    result = []
    for index, source in enumerate(predecessors):
        result.append({'id': 'base-'+str(index+1).zfill(2), 'name': SOURCE_LABELS[index],
                       'file': source['file'], 'sha256': source['sha256'], 'positions': source['blocks'],
                       'receipt_file': FIXED_RECEIPTS[index],
                       'receipt_sha256': source['native_verification']['receipt_sha256'],
                       'tier': 'historical_native_geometry'})
    districts = evidence['districts']
    if {r['district'] for r in districts} != {'castle', 'village', 'pirate-port', 'south-bank', 'harbor-quays'}:
        raise UserError('All five completed detail districts are required')
    for row in districts:
        proof = row['native']['after']
        result.append({'id': 'detail-'+row['district'], 'name': row['district']+' detail pass',
                       'file': 'detail-'+row['district']+'-'+row['construction_sha256']+'.json',
                       'sha256': row['construction_sha256'], 'positions': row['placements'],
                       'receipt_file': proof['archive_basename'],
                       'receipt_sha256': proof['archive_sha256'], 'tier': 'historical_native_geometry'})
    bridge = bounded_json(Path(repo)/'evidence/runtime/drawbridge-candidate.23.json')
    result.append({'id': 'settled-bridge-overlay', 'name': 'Settled 55-degree drawbridge verification overlay',
                   'file': None, 'sha256': bridge['closed_geometry']['plan_sha256'],
                   'positions': bridge['closed_geometry']['blocks'],
                   'receipt_file': 'drawbridge-settled-hydraulics-native-verify-candidate23.json',
                   'receipt_sha256': bridge['closed_geometry_receipt_sha256'],
                   'tier': 'historical_native_geometry', 'verification_only': True})
    return result


def native_proof(plan, proof, policy):
    if (proof.get('operation') != 'verify' or proof.get('plan_sha256') != policy['sha256']
            or proof.get('failures') != 0 or proof.get('error') or not proof.get('finished')
            or proof.get('blocks') != len(plan['blocks']) or len(plan['blocks']) != policy['positions']):
        raise UserError('No successful exact native geometry proof: '+policy['id'])
    return {'operation': 'verify', 'plan_sha256': policy['sha256'], 'failures': 0,
            'positions': len(plan['blocks']), 'finished': proof['finished'],
            'receipt_sha256': policy['receipt_sha256']}


def landmark_for(position, landmarks, fallback):
    if landmarks:
        nearest = min(landmarks, key=lambda r: (r['x']-position[0])**2+(r['z']-position[2])**2)
        if math.hypot(nearest['x']-position[0], nearest['z']-position[2]) <= 100:
            return str(nearest['name']), [nearest['x'], nearest['y'], nearest['z']]
    return fallback, list(position)


def namespace_counts(ids):
    return dict(sorted(Counter(value.split(':', 1)[0] for value in ids).items()))


def aggregate_geometry(directory, registry, policies):
    """Last writer wins; only mod blocks are retained, limiting memory during gameplay."""
    blocks, vanilla, inventory, actions, sources, landmarks_all, warnings = {}, {}, {}, [], [], [], []
    anchor_ids = set().union(*VANILLA_ANCHORS.values())
    registry_items, registry_entities = set(registry['items']), set(registry['entities'])
    world = registry.get('seed'), registry.get('world_path')
    for policy in policies:
        filename = policy['file']
        if filename is None:
            matches = []
            for path in directory.glob('drawbridge-settled-hydraulics-verify-*/*VERIFY-ONLY.json'):
                if path.stat().st_size <= MAX_PLAN and digest(path) == policy['sha256']:
                    matches.append(path)
            if len(matches) != 1:
                raise UserError('Expected the exact settled bridge verification derivative')
            path = matches[0]
        else:
            if Path(filename).name != filename:
                raise UserError('Construction evidence path must be a basename')
            path = directory/filename
        plan = bounded_json(path, MAX_PLAN)
        if digest(path) != policy['sha256'] or plan.get('format') != 'awft-native-settlement:1':
            raise UserError('Reviewed construction plan bytes changed: '+policy['id'])
        if (plan.get('seed'), plan.get('world_path')) != world:
            raise UserError('Construction evidence mixes distinct worlds')
        receipt = directory/policy['receipt_file']
        if digest(receipt) != policy['receipt_sha256']:
            raise UserError('Archived native receipt bytes changed: '+policy['id'])
        proof = native_proof(plan, bounded_json(receipt), policy)
        sources.append({**{k: policy[k] for k in ('id', 'name', 'sha256', 'positions', 'tier')},
                        'file': path.name, 'native_verification': proof,
                        'verification_only': policy.get('verification_only', False)})
        landmarks = plan.get('landmarks', [])
        for row in landmarks:
            landmarks_all.append({'name': str(row['name']), 'position': [row['x'], row['y'], row['z']],
                                  'source': policy['id']})
        palette = [state.split('[', 1)[0] for state in plan['palette']]
        if any(block not in registry['blocks'] for block in palette):
            raise UserError('A construction block is absent from the actual native registry')
        for x, y, z, index in plan['blocks']:
            pos = x, y, z
            inventory.pop(pos, None)
            vanilla.pop(pos, None)
            block = palette[index]
            if block.startswith('minecraft:'):
                blocks.pop(pos, None)
                if block in anchor_ids:
                    name, center = landmark_for(pos, landmarks, policy['name'])
                    vanilla[pos] = block, policy['id'], name, tuple(center)
            else:
                name, center = landmark_for(pos, landmarks, policy['name'])
                blocks[pos] = block, policy['id'], name, tuple(center)
        for row in plan.get('block_entities', []):
            pos = tuple(row['pos'])
            nbt = SNBT(row['nbt']).read()
            if 'Items' not in nbt:
                continue
            if not isinstance(nbt['Items'], list):
                raise UserError('Unsupported supplied inventory shape')
            items = []
            for item in nbt['Items']:
                if (not isinstance(item, dict) or not ID.fullmatch(str(item.get('id', '')))
                        or type(item.get('count')) is not int or not 0 < item['count'] <= 4096
                        or item['id'] not in registry_items):
                    raise UserError('Supplied inventory ID/count is not native')
                items.append({'id': item['id'], 'count': item['count']})
            inventory[pos] = (items, policy['id'], *landmark_for(pos, landmarks, policy['name']))
        for command in plan.get('commands', []):
            match = re.fullmatch(r'summon ([a-z0-9_.-]+:[a-z0-9_./-]+) ([-+.\d]+) ([-+.\d]+) ([-+.\d]+) (\{.*\})', command)
            if not match:
                warnings.append({'source': policy['id'], 'kind': 'non-summon construction action',
                                 'note': 'Not counted as a supplied mod entity or functional feature'})
                continue
            entity = match[1]
            if entity not in registry_entities:
                raise UserError('Construction summon is absent from the actual native entity registry')
            pos = [float(match[n]) for n in (2, 3, 4)]
            nbt = SNBT(match[5]).read()
            name, center = landmark_for(pos, landmarks, policy['name'])
            actions.append({'entity': entity, 'position': pos, 'source': policy['id'],
                            'exhibit': name, 'exhibit_position': center,
                            'no_ai': bool(nbt.get('NoAI', 0)),
                            'evidence': 'summon in historically verified construction plan; no fresh entity/behavior check'})
    grouped = {}
    for pos, (block, source, name, center) in sorted(blocks.items()):
        namespace = block.split(':', 1)[0]
        key = namespace, source, name
        row = grouped.setdefault(key, {'namespace': namespace, 'source': source, 'exhibit': name,
                                       'exhibit_position': list(center), 'blocks': 0,
                                       'block_types': Counter(), 'sample_positions': []})
        row['blocks'] += 1
        row['block_types'][block] += 1
        if len(row['sample_positions']) < 3:
            row['sample_positions'].append(list(pos))
    presence = []
    for key in sorted(grouped):
        row = grouped[key]
        row['block_types'] = dict(sorted(row['block_types'].items()))
        presence.append(row)
    items_grouped = {}
    for pos, (items, source, name, center) in sorted(inventory.items()):
        for item in items:
            key = item['id'], source, name
            row = items_grouped.setdefault(key, {'id': item['id'], 'source': source, 'exhibit': name,
                                                 'exhibit_position': center, 'count': 0, 'containers': []})
            row['count'] += item['count']
            if list(pos) not in row['containers']:
                row['containers'].append(list(pos))
    vanilla_grouped = {}
    for pos, (block, source, name, center) in sorted(vanilla.items()):
        key = block, source, name
        row = vanilla_grouped.setdefault(key, {'block': block, 'source': source, 'exhibit': name,
                                               'exhibit_position': list(center), 'count': 0,
                                               'sample_positions': []})
        row['count'] += 1
        if len(row['sample_positions']) < 3:
            row['sample_positions'].append(list(pos))
    return {'sources': sources, 'blocks': presence,
            'vanilla_stations': [vanilla_grouped[key] for key in sorted(vanilla_grouped)],
            'supplied_items': [items_grouped[key] for key in sorted(items_grouped)],
            'construction_summons': sorted(actions, key=lambda r: (r['entity'], r['source'], r['position'])),
            'landmarks': sorted(landmarks_all, key=lambda r: (r['name'], r['source'], r['position'])),
            'warnings': warnings, 'composite_mod_block_positions': len(blocks)}


def functional_policy(repo=REPO):
    """Explicitly admitted scope; an arbitrary hash-shaped input cannot create a pass."""
    path = Path(repo)/'evidence/runtime/drawbridge-candidate.23.json'
    bridge = bounded_json(path)
    cycles = bridge['cycles']
    if (cycles.get('operation') != 'commission' or cycles.get('cycles') != 2
            or not cycles.get('finished') or cycles.get('cleanup_required') is not False
            or cycles.get('temporary_tickets_remaining') != 0
            or cycles.get('temporary_tickets_released') != cycles.get('temporary_tickets')):
        raise UserError('Public drawbridge evidence does not admit a completed native cycle pass')
    return [{'id': 'drawbridge-55-native', 'mod_ids': ['create', 'awft_control_bridge'],
             'pack_sha256': bridge['pack_sha256'], 'receipt_sha256': bridge['native_cycle_receipt_sha256'],
             'public_evidence': 'evidence/runtime/drawbridge-candidate.23.json',
             'public_evidence_sha256': digest(path), 'finished': cycles['finished'],
             'status': 'passed_scoped_native_behavior', 'temporary_tickets_remaining': 0}]


def staged_inputs(home):
    """Read only exact reviewed stage bundles; never promote a stage to native evidence."""
    home = Path(home)
    result = []
    maritime_dir = home/'staging/maritime-attractions-ef0339c44aad869d'
    manifest_path = maritime_dir/'manifest.json'
    expected = '7c4e034450337d5c51394b4db339d4624f66335ecf80c34a6665fcda87e0ee5c'
    if digest(manifest_path) != expected:
        raise UserError('Reviewed maritime stage changed; preserve and explicitly review its successor')
    manifest = bounded_json(manifest_path)
    proposal_path = maritime_dir/'proposal.json'
    if digest(proposal_path) != manifest['documents']['proposal.json']['sha256']:
        raise UserError('Maritime stage proposal changed')
    maritime = bounded_json(proposal_path)
    result.extend([
        {'id': 'maritime-cog', 'name': 'The Sea Glass Promise sailing cog',
         'namespace': 'smallships', 'position': [1196.5, 63.1, -1264.5],
         'manifest_sha256': expected, 'plan_sha256': digest(proposal_path),
         'status': 'staged', 'native_placed': False,
         'features': ['Actual proposed smallships:cog, shared cargo and boarding finger pier'],
         'remaining': ['Fresh spatial occupancy and body clearance admission', 'Actual spawn/board/sail',
                       'Two-player use and restart']},
        {'id': 'maritime-hoist', 'name': 'Resolute tender cradle', 'namespace': 'create',
         'position': [1156, 77, -1440], 'manifest_sha256': expected,
         'plan_sha256': digest(proposal_path), 'status': 'staged', 'native_placed': False,
         'features': ['52-block hand-cranked native pulley cradle; empty vanilla tender only'],
         'remaining': ['Native verification of planned full tender-body sweep and spatial occupancy admission',
                       'Native assembly, lift, collision, boat retention and restart']},
        {'id': 'maritime-cache', 'name': maritime['discovery']['name'], 'namespace': 'minecraft',
         'position': maritime['discovery']['chest'], 'manifest_sha256': expected,
         'plan_sha256': digest(proposal_path), 'status': 'staged', 'native_placed': False,
         'features': ['Four-block-deep marked dive and one modest vanilla reward chest'],
         'remaining': ['Native swimming, breathing, visibility and return path',
                       'Does not demonstrate Treasure2 or Whaleborne mechanics']},
    ])
    engineering_path = home/'dashboard/settlement/attractions-9cda741f4682b851/manifest.json'
    expected = '9cda741f4682b851eb8c21b98dacc9088109a078cac2b4baff80cf6564be6be5'
    if digest(engineering_path) != expected:
        raise UserError('Reviewed engineering stage changed')
    engineering = bounded_json(engineering_path)
    plan_path = engineering_path.parent/engineering['plan_file']
    if digest(plan_path) != engineering['plan_sha256']:
        raise UserError('Engineering stage plan changed')
    planned = bounded_json(plan_path, MAX_PLAN)
    systems = engineering['systems']
    bench = next(([x, y, z] for x, y, z, index in planned['blocks']
                  if planned['palette'][index].split('[', 1)[0] == 'handcrafted:spruce_bench'), None)
    if bench is None:
        raise UserError('Reviewed garden halt stage has no actual bench')
    for ident, namespace, position, features in (
            ('mill', 'create', systems['watermill']['millstone'], ['Three stopped water wheels, real drivetrain, wheat mill/chute/hopper and press/depot']),
            ('pneumatics', 'overpressure', systems['pneumatic']['pump'], ['Filtered flour extraction, cog-driven pump, real tube route and inserter']),
            ('hypertube', 'create_hypertube', systems['hypertube']['entrances'][0], ['Two entrance candidates, midpoint and two required native 30-block Bezier spans']),
            ('railway', 'railways', systems['railway']['stations'][0]['position'], ['103 spruce tracks, two targeted stations and a two-bogey unassembled carriage']),
            ('halt-seats', 'handcrafted', bench, ['Usable garden halt bench candidates'])):
        result.append({'id': 'engineering-'+ident, 'name': 'East-castle '+ident, 'namespace': namespace,
                       'position': position, 'manifest_sha256': expected, 'plan_sha256': engineering['plan_sha256'],
                       'status': 'staged', 'native_placed': False, 'features': features,
                       'remaining': ['Fresh prior-state admission', 'Native placement and exact verification',
                                     'Native curve/assembly/power initialization as appropriate',
                                     'Actual gameplay and restart']})
    return result


def collect(home, repo=REPO):
    repo, home = Path(repo), Path(home)
    lock = bounded_json(repo/'catalog/lock.json')
    registry_path = home/'dashboard/settlement/registry.json'
    registry = bounded_json(registry_path)
    policies = source_policy(repo)
    geometry = aggregate_geometry(registry_path.parent, registry, policies)
    artifacts = [read_jar_identity(home/'caches/mods'/row['filename'], row)
                 for row in sorted(lock['mods'], key=lambda r: r['slug']) if row.get('kind', 'mod') == 'mod']
    namespace = defaultdict(lambda: {'blocks': 0, 'items': 0, 'entities': 0})
    for kind in ('blocks', 'items', 'entities'):
        for name, count in namespace_counts(registry[kind]).items():
            namespace[name][kind] = count
    bridge_path = repo/'evidence/runtime/drawbridge-candidate.23.json'
    bridge = bounded_json(bridge_path)
    raw_bridge = home/'dashboard/settlement/drawbridge-two-cycles55-candidate23.json'
    if digest(raw_bridge) != bridge['native_cycle_receipt_sha256']:
        raise UserError('Exact native drawbridge functional receipt changed')
    raw = bounded_json(raw_bridge)
    if (raw.get('operation') != 'commission' or raw.get('cleanup_required') is not False
            or not raw.get('finished') or raw.get('temporary_tickets') != raw.get('temporary_tickets_released')
            or len(raw.get('systems', [])) != 2
            or any(s.get('sequencer', {}).get('program_open_degrees') != 55 for s in raw['systems'])):
        raise UserError('Drawbridge commissioning is not a completed 55-degree acceptance receipt')
    functional = [{'id': 'drawbridge-55-native', 'mod_ids': ['create', 'awft_control_bridge'],
                   'name': 'Grand River Drawbridge: two native 55-degree open/close cycles',
                   'position': [1199, 70, -1144], 'status': 'passed_scoped_native_behavior',
                   'pack_sha256': bridge['pack_sha256'], 'receipt_sha256': digest(raw_bridge),
                   'public_evidence': 'evidence/runtime/drawbridge-candidate.23.json',
                   'public_evidence_sha256': digest(bridge_path),
                   'finished': raw['finished'], 'temporary_tickets_remaining': 0,
                   'remaining': ['Post-restart cycles', 'Rigged vessel clearance', 'Actual player/graphics review']}]
    result = {'format': FORMAT, 'candidate': lock['version'],
              'lock_sha256': digest(repo/'catalog/lock.json'), 'pack_sha256': digest(repo/'packwiz/pack.toml'),
              'registry_sha256': digest(registry_path), 'registry_at': registry.get('at'),
              'native_namespaces': dict(sorted(namespace.items())),
              'server_mod_ids': sorted({row['id'] for row in registry['mods']}),
              'artifacts': artifacts, 'geometry': geometry, 'staged': staged_inputs(home),
              'functional': functional}
    if len(encoded(result)) > MAX_INPUT:
        raise UserError('Thin sanitized showcase input exceeds 16 MiB')
    return result


def pin_equal(actual, expected):
    return all(actual.get(key) == expected.get(key) for key in ('filename', 'size', 'hashes'))


def request_mapping(lock, compatibility):
    files = {row['filename']: row for row in lock['mods']}
    by_slug, requests = defaultdict(list), []
    for request in sorted(compatibility['requests'], key=lambda r: r['id']):
        matched = []
        for key in ('file_pin', 'selected_alternative_pin'):
            pin = request.get(key)
            if pin is None:
                continue
            filename = pin.get('filename')
            actual = files.get(filename)
            if (actual is None or not pin_equal(pin, actual)
                    or pin.get('project_id') != actual.get('project_id')
                    or pin.get('version_id') != actual.get('version_id')):
                raise UserError('Canonical request mapping has a stale or unknown file pin: '+request['id'])
            by_slug[actual['slug']].append({'id': request['id'], 'name': request['name'],
                                           'group': request.get('group'), 'mapping': key})
            matched.append({'slug': actual['slug'], 'kind': actual.get('kind', 'mod'), 'mapping': key})
        requests.append({'id': request['id'], 'name': request['name'], 'status': request['status'],
                         'selected_files': matched})
    return by_slug, requests


def role_for(ids, side, mode):
    if not ids:
        if mode in ('LIBRARY', 'LANGPROVIDER'):
            return 'library', 'Native FML '+mode+' declaration; support runtime rather than a physical exhibit.', False
        return 'needs_identity_review', 'No supported root mod declaration or FML library classification; do not infer identity from its slug.', True
    if all(ident in LIBRARIES for ident in ids):
        return 'library', 'Declared support/API module; test through its dependent feature. No independent decorative exhibit is required.', False
    if all(ident in PERFORMANCE for ident in ids):
        return 'performance', 'Requires controlled before/after measurements and compatibility checks; scenery cannot demonstrate its benefit.', False
    if any(ident in WORLD_GENERATION for ident in ids):
        return 'generated_world', 'Visit naturally generated content with provenance. A hand-built themed structure does not demonstrate this generator.', False
    if all(ident in BACKGROUND for ident in ids):
        return 'service', ' '.join(BACKGROUND[ident] for ident in ids), False
    if side == 'client' or any(ident in CLIENT_GOALS for ident in ids):
        return 'client_feature', 'Check the actual client feature/UI/rendering with the pinned pack; no physical exhibit proxy is needed.', False
    if any(ident in GOALS for ident in ids):
        return 'gameplay_content', 'Meaningful in-world use or an intentionally complete furnishing sample is required; item/block presence is only partial coverage.', True
    return 'needs_feature_review', 'Declared identity is known, but its demonstration contract needs explicit review; absence of a namespace is not an exemption.', True


def validate_inputs(inputs, lock, compatibility, lock_sha, pack_sha, policies, functional_policies):
    if (inputs.get('format') != FORMAT or inputs.get('candidate') != lock['version']
            or inputs.get('lock_sha256') != lock_sha or inputs.get('pack_sha256') != pack_sha):
        raise UserError('Showcase inputs do not belong to the exact current pack/lock')
    expected = compatibility.get('source_lock', {})
    if expected.get('sha256') != lock_sha or expected.get('pack_sha256') != pack_sha:
        raise UserError('Canonical compatibility mapping is stale')
    if not SHA.fullmatch(inputs.get('registry_sha256', '')):
        raise UserError('Missing exact native registry provenance')
    pins = [r for r in lock['mods'] if r.get('kind', 'mod') == 'mod']
    artifact_rows = inputs.get('artifacts', [])
    artifact_map = {row['filename']: row for row in artifact_rows}
    if len(artifact_map) != len(artifact_rows) or set(artifact_map) != {p['filename'] for p in pins}:
        raise UserError('Every pinned mod JAR, including disabled optional mods, needs one identity record')
    for pin in pins:
        artifact = artifact_map[pin['filename']]
        if not pin_equal(artifact, pin):
            raise UserError('Showcase JAR identity pin changed: '+pin['filename'])
        if any(not SHA.fullmatch(row.get('sha256', '')) or not row.get('member')
               for row in artifact.get('metadata', [])):
            raise UserError('Actual native declaration metadata lacks exact member hashes')
    source_rows = inputs.get('geometry', {}).get('sources', [])
    source_map = {r['id']: r for r in source_rows}
    if len(source_rows) != len(source_map) or set(source_map) != {p['id'] for p in policies}:
        raise UserError('Showcase native source set is missing or contains unknown evidence')
    for policy in policies:
        row = source_map[policy['id']]
        proof = row.get('native_verification', {})
        if (row.get('sha256') != policy['sha256'] or row.get('positions') != policy['positions']
                or proof.get('receipt_sha256') != policy['receipt_sha256']
                or proof.get('operation') != 'verify' or proof.get('failures') != 0
                or proof.get('plan_sha256') != policy['sha256']
                or proof.get('positions') != policy['positions'] or not proof.get('finished')):
            raise UserError('Showcase native provenance changed: '+policy['id'])
    for kind in ('blocks', 'vanilla_stations', 'supplied_items', 'construction_summons'):
        for row in inputs['geometry'].get(kind, []):
            if row.get('source') not in source_map:
                raise UserError('Unknown native source attributed to '+kind)
    seen = set()
    total = 0
    for row in inputs['geometry'].get('blocks', []):
        key = row['namespace'], row['source'], row['exhibit']
        if (key in seen or type(row.get('blocks')) is not int or row['blocks'] < 1
                or row['blocks'] > source_map[row['source']]['positions']
                or any(not ID.fullmatch(k) or k.split(':', 1)[0] != row['namespace']
                       or type(v) is not int or v < 1 for k, v in row.get('block_types', {}).items())
                or sum(row.get('block_types', {}).values()) != row['blocks']):
            raise UserError('Composite block counts/types/provenance are inconsistent')
        total += row['blocks']
        seen.add(key)
    if total != inputs['geometry'].get('composite_mod_block_positions'):
        raise UserError('Composite mod-block count is not the sum of its distinct source/exhibit groups')
    for row in inputs['geometry'].get('supplied_items', []):
        if not ID.fullmatch(row.get('id', '')) or type(row.get('count')) is not int or row['count'] < 1:
            raise UserError('Invalid supplied item record')
    for row in inputs.get('staged', []):
        if row.get('status') != 'staged' or row.get('native_placed') is not False:
            raise UserError('A source-only attraction cannot become placed/accepted evidence')
        if not all(SHA.fullmatch(row.get(key, '')) for key in ('manifest_sha256', 'plan_sha256')):
            raise UserError('Missing exact staged provenance')
    expected_functions = {row['id']: row for row in functional_policies}
    actual_functions = inputs.get('functional', [])
    if (len(actual_functions) != len(expected_functions)
            or {r['id'] for r in actual_functions} != set(expected_functions)):
        raise UserError('Unknown or missing scoped functional evidence')
    for row in actual_functions:
        expected_function = expected_functions[row['id']]
        if any(row.get(key) != value for key, value in expected_function.items()):
            raise UserError('Scoped functional evidence differs from its explicitly admitted receipt')


def build_report(lock, compatibility, inputs, *, lock_sha, pack_sha, policies, functional_policies=()):
    validate_inputs(inputs, lock, compatibility, lock_sha, pack_sha, policies, functional_policies)
    request_by_slug, requests = request_mapping(lock, compatibility)
    artifacts = {row['filename']: row for row in inputs['artifacts']}
    owner, identities = defaultdict(list), {}
    for pin in lock['mods']:
        if pin.get('kind', 'mod') != 'mod':
            continue
        meta = artifacts[pin['filename']]
        roots = [r['id'] for r in meta['declared_mods']]
        if len(set(roots)) != len(roots) or any(not MOD_ID.fullmatch(v) for v in roots):
            raise UserError('Duplicate or invalid actual root mod IDs')
        embedded = {r['id'] for r in meta.get('embedded_mods', [])}
        namespaces = set(roots)
        for ident in roots:
            aliases = set(BUNDLE_NAMESPACES.get(ident, ()))
            if not aliases <= embedded:
                raise UserError('Feature bundle namespace lacks an actual embedded declaration')
            namespaces.update(aliases)
        identities[pin['slug']] = roots, sorted(namespaces)
        for namespace in namespaces:
            owner[namespace].append(pin['slug'])
    ambiguous = {key: sorted(value) for key, value in owner.items() if len(value) > 1}
    if ambiguous:
        raise UserError('Ambiguous actual mod namespace ownership: '+str(ambiguous))
    geom = inputs['geometry']
    rows, disabled = [], []
    for pin in sorted((p for p in lock['mods'] if p.get('kind', 'mod') == 'mod'), key=lambda r: r['slug']):
        roots, namespaces = identities[pin['slug']]
        metadata = artifacts[pin['filename']]
        role, reason, physical = role_for(roots, pin['side'], metadata.get('fml_mod_type'))
        blocks = [r for r in geom['blocks'] if r['namespace'] in namespaces]
        items = [r for r in geom['supplied_items'] if r['id'].split(':', 1)[0] in namespaces]
        summons = [r for r in geom['construction_summons'] if r['entity'].split(':', 1)[0] in namespaces]
        vanilla_ids = set().union(*(VANILLA_ANCHORS.get(ident, set()) for ident in roots))
        vanilla_stations = [r for r in geom.get('vanilla_stations', []) if r['block'] in vanilla_ids]
        staged = [r for r in inputs.get('staged', []) if r['namespace'] in namespaces]
        functional = [r for r in inputs.get('functional', []) if set(r['mod_ids']) & set(roots)]
        if any(r.get('status') != 'passed_scoped_native_behavior' or r.get('pack_sha256') != pack_sha
               or not SHA.fullmatch(r.get('receipt_sha256', '')) for r in functional):
            raise UserError('Functional receipt is not a scoped current-pack proof')
        goals = [GOALS[ident] for ident in roots if ident in GOALS]
        goals += [CLIENT_GOALS[ident] for ident in roots if ident in CLIENT_GOALS]
        if not goals:
            if role == 'generated_world':
                goals = ['Visit an actual generated biome/structure and record identity, coordinates, safe access and two-player discovery. Avoid forcing new generation for a display.']
            elif role == 'performance':
                goals = ['Run a controlled representative baseline/candidate comparison for CPU, RAM, frame time or server ticks as appropriate; record overhead and correctness.']
            elif role == 'client_feature':
                goals = ['Check the actual named client feature with both intended profiles; record rendering/UI/audio and behavior independently from server geometry.']
            elif role == 'library':
                goals = ['Verify dependent features load and behave correctly; retain exact API/dependency pins.']
            else:
                goals = [reason]
        if role.startswith('needs_'):
            coverage = 'needs_review'
        elif functional:
            coverage = 'scoped_behavior_passed_other_features_pending'
        elif physical:
            coverage = 'partial_presence_only' if blocks or items or summons else 'missing_actual_demonstration'
        else:
            coverage = 'feature_check_pending_no_physical_proxy_required'
        row = {'slug': pin['slug'], 'name': pin['name'], 'version': pin['version'],
               'file_pin': {key: pin[key] for key in ('filename', 'size', 'hashes')},
               'side': pin['side'], 'enabled_by_default': not pin.get('optional', False) or pin.get('default', True),
               'declared_mods': metadata['declared_mods'], 'feature_namespaces': namespaces,
               'identity_metadata': metadata['metadata'], 'fml_mod_type': metadata.get('fml_mod_type'),
               'canonical_requests': sorted(request_by_slug[pin['slug']], key=lambda r: (r['id'], r['mapping'])),
               'role': role, 'classification_reason': reason, 'physical_exhibit_expected': physical,
               'coverage': coverage, 'native_registry_counts': {n: inputs['native_namespaces'].get(n, {'blocks': 0, 'items': 0, 'entities': 0}) for n in namespaces},
               'historical_mod_blocks': sum(r['blocks'] for r in blocks), 'placed_exhibits': blocks,
               'supplied_item_count': sum(r['count'] for r in items), 'supplied_items': items,
               'construction_summon_count': len(summons), 'construction_summons': summons,
               'related_vanilla_station_count': sum(r['count'] for r in vanilla_stations),
               'related_vanilla_stations': vanilla_stations,
               'staged_attractions': staged, 'scoped_functional_checks': functional,
               'demonstration_goals': goals,
               'pending': ['Actual feature/player acceptance remains unverified unless the exact scoped receipt above says otherwise.']}
        if role == 'library' and (blocks or items or summons):
            row['pending'].append('This support module has native content present; inspect that content explicitly rather than blanket-exempting its behavior.')
        (rows if row['enabled_by_default'] else disabled).append(row)
    unknown = sorted({r['namespace'] for r in geom['blocks']} - set(owner))
    unknown += sorted({r['id'].split(':', 1)[0] for r in geom['supplied_items']} - set(owner) - {'minecraft'})
    unknown += sorted({r['entity'].split(':', 1)[0] for r in geom['construction_summons']} - set(owner) - {'minecraft'})
    priorities = []
    for ident in PRIORITY:
        for row in rows:
            if ident in row['feature_namespaces']:
                priorities.append({'mod_id': ident, 'slug': row['slug'], 'name': row['name'],
                                   'coverage': row['coverage'], 'historical_mod_blocks': row['historical_mod_blocks'],
                                   'supplied_item_count': row['supplied_item_count'],
                                   'construction_summons': row['construction_summon_count'],
                                   'staged': [r['id'] for r in row['staged_attractions']],
                                   'needed': row['demonstration_goals'][0]})
    totals = {'enabled_mod_jars': len(rows), 'disabled_optional_mod_jars': len(disabled),
              'all_pinned_mod_jars': len(rows)+len(disabled), 'canonical_requests': len(requests),
              'native_geometry_sources': len(geom['sources']), 'base_plans': 10, 'detail_passes': 5,
              'settled_bridge_overlays': 1, 'historical_mod_block_positions': geom['composite_mod_block_positions'],
              'mods_with_historical_mod_blocks': sum(bool(r['historical_mod_blocks']) for r in rows),
              'mods_with_supplied_items': sum(bool(r['supplied_item_count']) for r in rows),
              'mods_with_construction_summons': sum(bool(r['construction_summon_count']) for r in rows),
              'mods_with_related_vanilla_stations': sum(bool(r['related_vanilla_station_count']) for r in rows),
              'physical_exhibit_mods': sum(r['physical_exhibit_expected'] for r in rows),
              'physical_mods_without_any_presence': sum(r['physical_exhibit_expected'] and not (r['historical_mod_blocks'] or r['supplied_item_count'] or r['construction_summon_count']) for r in rows),
              'scoped_functional_demonstrations': len(inputs.get('functional', [])),
              'mods_with_scoped_functional_receipts': sum(bool(r['scoped_functional_checks']) for r in rows),
              'fully_accepted_mods': 0, 'staged_attractions': len(inputs.get('staged', [])),
              'unattributed_namespaces': len(set(unknown)),
              'roles': dict(sorted(Counter(r['role'] for r in rows).items()))}
    report = {'format': REPORT_FORMAT, 'candidate': lock['version'], 'generated': lock['generated'],
              'generation_basis': 'Frozen lock timestamp; exact sanitized input bytes; deterministic sorted output',
              'lock_sha256': lock_sha, 'pack_sha256': pack_sha, 'input_sha256': sha_bytes(encoded(inputs)),
              'native_registry_sha256': inputs['registry_sha256'], 'native_registry_at': inputs.get('registry_at'),
              'evidence_boundary': ['Historical native block/inventory geometry, not a fresh live-world scan.',
                                    'Last-writer composite: ten base plans, five detail passes, then settled bridge verification overlay.',
                                    'Items are construction-supplied stocks; current inventories/ownership are not rechecked.',
                                    'Construction summons are source actions, not fresh live entity or normal-AI proof.',
                                    'Staged attractions have no world placement or gameplay acceptance.',
                                    'Client/render/performance/background features require their own checks; no invented physical exhibit exemption for unknown mods.',
                                    'A scoped native drawbridge pass is not complete pack or two-player acceptance.'],
              'totals': totals, 'native_geometry_sources': geom['sources'],
              'landmarks': geom['landmarks'], 'priority_gaps': priorities,
              'unattributed_namespaces': sorted(set(unknown)), 'audit_warnings': geom['warnings'],
              'mods': rows, 'disabled_optional_mods': disabled,
              'canonical_request_coverage': requests, 'staged_attractions': inputs.get('staged', [])}
    assert_public(report)
    return report


def assert_public(value):
    """Reject sensitive field names and absolute local paths before any public write."""
    forbidden = {'seed', 'world_path', 'backup_id', 'backup_sha256', 'base_backup_id',
                 'base_backup_sha256', 'accounts', 'access_token', 'session_token', 'uuid'}
    def walk(row):
        if isinstance(row, dict):
            for key, child in row.items():
                if key.lower() in forbidden:
                    raise UserError('Sensitive field reached public showcase output: '+key)
                walk(child)
        elif isinstance(row, list):
            for child in row:
                walk(child)
        elif isinstance(row, str):
            if re.search(r'(?i)(?<![a-z0-9])[a-z]:[\\/]|C:\\Users|D:\\A World', row):
                raise UserError('Absolute local path reached public showcase output')
    walk(value)


def markdown(report):
    t = report['totals']
    lines = ['# Showcase coverage', '',
             f"Candidate **{report['candidate']}** has **{t['enabled_mod_jars']} enabled mod JARs**, plus "
             f"**{t['disabled_optional_mod_jars']} disabled optional mod**. This is an auditable coverage report, not completion or multiplayer acceptance.", '',
             f"The historical composite contains **{t['historical_mod_block_positions']:,} mod-block positions** across "
             f"**{t['mods_with_historical_mod_blocks']} mod artifacts**. "
             f"**{t['mods_with_supplied_items']}** artifacts have supplied items and "
             f"**{t['mods_with_construction_summons']}** have summons in construction plans. "
             f"Of **{t['physical_exhibit_mods']}** artifacts needing meaningful physical demonstrations, "
             f"**{t['physical_mods_without_any_presence']}** have no mod-owned block/item/summon evidence. "
             'Presence in the remaining rows is partial evidence; it does not establish working gameplay.', '',
             f"**{t['mods_with_related_vanilla_stations']}** mods have related real vanilla interaction sites "
             '(including crafting tables and furnaces). These are reported separately from mod-owned blocks; '
             'their presence does not establish the mod behavior.', '',
             'The sole scoped functional demonstration recorded here is the Grand River Drawbridge: '
             'two native 55-degree open/close cycles with all 11 temporary tickets released. '
             'That receipt covers Create and the Control Room bridge integration. '
             'Post-restart cycles, rigged-vessel clearance, player traversal and visual review remain separate.', '',
             '## What the evidence means', '',
             '- **Placed blocks:** exact archived native checks for ten base plans and five detail passes, overlaid by the settled bridge verification. Last writer wins; overlap is not double-counted.',
             '- **Supplied items:** explicit native item IDs and counts in archived planned inventories. These may have changed during play; their presence is not a completed crafting/delivery/fishing loop.',
             '- **Construction summons:** real entity IDs in verified construction plans. This report does not infer current entity survival, normal AI or sailing from a summon command.',
             '- **Related vanilla stations:** real crafting tables, furnaces or other potential interaction sites are listed for mods using vanilla blocks. Their presence does not verify the mod interaction.',
             '- **Staged:** source plans only. No physical, functional or player acceptance is claimed.',
             '- **Library, client, performance and service features:** an explicit classification gives the appropriate check. Unknown identities/features stay under review.', '',
             '## Priority missing demonstrations', '']
    for row in report['priority_gaps']:
        stage = '; staged '+', '.join(row['staged']) if row['staged'] else ''
        lines.append(f"- **{row['name']}** (`{row['mod_id']}`): {row['historical_mod_blocks']} blocks, "
                     f"{row['supplied_item_count']} supplied items, {row['construction_summons']} construction summons{stage}. {row['needed']}")
    lines += ['', 'The underwater Sea Glass Cache is a staged, modest vanilla-chest dive. '
              'Its swimming, breathing, visibility and return route need actual checks. '
              'It is not a Treasure2 or Whaleborne demonstration.', '', '## Staged attractions', '']
    for row in report['staged_attractions']:
        lines.append(f"- **{row['name']}** at `{', '.join(map(str,row['position']))}`: "
                     + '; '.join(row['features'])+'. **STAGED ONLY.** '+ '; '.join(row['remaining'])+'.')
    lines += ['', '## Every enabled mod JAR', '',
              'Actual mod IDs below come from native declarations inside the hash-checked pinned JARs. '
              'Aeronautics feature namespaces are its three explicitly declared embedded modules. '
              'Project slugs and directory names never establish identity. Counts describe historical construction, not an exhaustive live-world census.', '',
              '| Mod / actual ID | Class | Blocks / items / summons | Evidence and next check |',
              '| --- | --- | ---: | --- |']
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    for row in report['mods']:
        ids = ', '.join(r['id'] for r in row['declared_mods']) or 'FML '+str(row['fml_mod_type'])
        exhibits = sorted(row['placed_exhibits'], key=lambda r: (-r['blocks'], r['exhibit'], r['source']))
        if exhibits:
            first = exhibits[0]
            evidence = f"{first['exhibit']} ({', '.join(map(str, first['exhibit_position']))}); {len(exhibits)} source/exhibit groups. "
        elif row['supplied_item_count']:
            evidence = 'Supplied items only. '
        elif row['construction_summon_count']:
            evidence = 'Construction summons only; current AI unverified. '
        else:
            evidence = 'No physical presence counted. '
        if row['staged_attractions']:
            evidence += 'Staged: '+', '.join(r['name'] for r in row['staged_attractions'])+'. '
        if row['related_vanilla_station_count']:
            evidence += str(row['related_vanilla_station_count'])+' related vanilla stations; mod interaction pending. '
        if row['scoped_functional_checks']:
            evidence += 'Scoped native bridge cycles passed. '
        evidence += row['demonstration_goals'][0]
        lines.append('| '+cell(row['name'])+' / `'+cell(ids)+'` | '+cell(row['role'])+' | '
                     +f"{row['historical_mod_blocks']} / {row['supplied_item_count']} / {row['construction_summon_count']}"
                     +' | '+cell(evidence)+' |')
    lines += ['', '## Optional disabled mod', '']
    for row in report['disabled_optional_mods']:
        lines.append(f"- **{row['name']} {row['version']}**: disabled by default. "
                     'Its presence in the lock is not installed gameplay or remote-join acceptance; the public Playit address works independently of this option.')
    lines += ['', '## Exact provenance and regeneration', '',
              f"- Pack SHA-256: `{report['pack_sha256']}`.",
              f"- Lock SHA-256: `{report['lock_sha256']}`.",
              f"- Sanitized input SHA-256: `{report['input_sha256']}`.",
              f"- Native registry SHA-256: `{report['native_registry_sha256']}`.", '',
              'The machine-readable [catalogue](../catalog/showcase.json) contains every artifact pin, '
              'canonical request association, native source/receipt hash, exhibit coordinate, block-type count, supplied item, staged feature and scoped functional check. '
              'It includes all selected requests through the canonical compatibility mapping; unresolved requests remain there with no falsely invented selected artifact.', '',
              'Collection requires the private cached JARs, retained exact construction plans/receipts and staged manifests. '
              'It makes no Minecraft connection and runs no mod code. It validates those inputs and emits a bounded, sanitized private snapshot. '
              'Public output never contains world seeds, absolute home paths, accounts, entity UUIDs, credentials or backup data.', '',
              '```powershell',
              'python -m tools.showcase_coverage collect --home "<private runtime home>" --output "<new private input snapshot>"',
              'python -m tools.showcase_coverage render --inputs "<private input snapshot>"',
              'python -m tools.showcase_coverage render --inputs "<private input snapshot>" --check',
              '```', '',
              'Repeated rendering from identical inputs is byte-for-byte deterministic. A changed pack, JAR pin, native receipt or unreviewed source invalidates the audit. '
              'Historical sources do not become fresh runtime proof merely by regenerating this report. '
              'The reserve guard covers this bounded writer; external applications and existing writers remain outside its control.', '']
    return '\n'.join(lines).encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    capture = sub.add_parser('collect')
    capture.add_argument('--home', required=True, type=Path)
    capture.add_argument('--output', required=True, type=Path)
    render = sub.add_parser('render')
    render.add_argument('--inputs', required=True, type=Path)
    render.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.command == 'collect':
        if args.output.exists():
            raise UserError('Preserve existing audit snapshots; select a new output filename')
        if os.name == 'nt' and args.output.resolve().drive.upper() != 'D:':
            raise UserError('Private audit snapshots must be staged on D:')
        reserve(1024**2, MAX_INPUT)
        result = collect(args.home)
        assert_public(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(args.output, encoded(result))
        print(json.dumps({'file': str(args.output), 'bytes': args.output.stat().st_size,
                          'sha256': digest(args.output), 'native_world_operations': 0}))
    else:
        inputs = bounded_json(args.inputs)
        lock = bounded_json(REPO/'catalog/lock.json')
        compatibility = bounded_json(REPO/'catalog/compatibility.json')
        report = build_report(lock, compatibility, inputs,
                              lock_sha=digest(REPO/'catalog/lock.json'),
                              pack_sha=digest(REPO/'packwiz/pack.toml'), policies=source_policy(REPO),
                              functional_policies=functional_policy(REPO))
        outputs = {REPO/'catalog/showcase.json': encoded(report),
                   REPO/'docs/SHOWCASE-COVERAGE.md': markdown(report)}
        if sum(len(v) for v in outputs.values()) > MAX_INPUT:
            raise UserError('Public showcase report exceeds its finite output bound')
        if args.check:
            if any(not path.is_file() or path.read_bytes() != raw for path, raw in outputs.items()):
                raise UserError('Showcase report differs from its exact inputs')
        else:
            reserve(MAX_INPUT, 0)
            for path, raw in outputs.items():
                atomic_write(path, raw)
        print(json.dumps({'check': args.check, 'totals': report['totals']}))


if __name__ == '__main__':
    main()
