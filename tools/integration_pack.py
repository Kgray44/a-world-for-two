"""Build the small reviewed data overrides, preserving unrelated upstream data."""
from pathlib import Path
import json
import zipfile
from copy import deepcopy

from control_room.common import REPO, Layout, digest, read_json, write_json
from control_room.storage import Storage


def build(home=Path(r'D:\A World for Two')):
    layout = Layout(home)
    Storage(layout).reserve(1024 * 1024, REPO / 'packwiz')
    lock = read_json(REPO / 'catalog/lock.json')
    destination = REPO / 'packwiz/config/paxi/datapacks/awft-integration'
    write_json(destination / 'pack.mcmeta', {'pack': {'pack_format': 48, 'description': 'A World for Two: coastal pirate encounters and reviewed recipe repairs'}})
    sources = []
    def upstream(slug, name):
        item = next(m for m in lock['mods'] if m['slug'] == slug)
        jar = layout.caches / 'mods' / item['filename']
        if digest(jar, 'sha512') != item['hashes']['sha512']:
            raise ValueError('Unreviewed source bytes: ' + slug)
        with zipfile.ZipFile(jar) as archive:
            raw = archive.read(name)
        sources.append({'project': slug, 'version': item['version'], 'file': name, 'jar_sha256': digest(jar)})
        return json.loads(raw)
    for kind, tags in [('beaches', ['minecraft:is_beach', 'c:is_beach']), ('oceans', ['minecraft:is_ocean', 'c:is_ocean'])]:
        write_json(destination / f'data/awft/tags/worldgen/biome/pirate_{kind}.json',
                   {'replace': False, 'values': [{'id': '#' + t, 'required': False} for t in tags]})
    root = 'data/treasures_of_the_dead/neoforge/biome_modifier/'
    for name, kind in [('totd_skeleton_overworld_spawns.json', 'oceans'), ('totd_skeleton_spawns.json', 'beaches'), ('blooming_skeleton_spawns.json', 'oceans')]:
        data = upstream('treasures-of-the-dead', root + name)
        data['biomes'] = '#awft:pirate_' + kind
        for spawn in data['spawners']:
            captain = 'captain' in spawn['type']
            spawn.update(weight=3 if captain else 15, minCount=1, maxCount=1 if captain else 3)
        write_json(destination / root / name, data)
    path = 'data/createdeco/recipe/placard.json'
    recipe = upstream('create-deco', path)
    for ingredient in recipe['ingredients']:
        if ingredient.get('id') == 'minecraft:white_dye':
            ingredient['item'] = ingredient.pop('id')
    write_json(destination / path, recipe)
    # Preserve Visual Workbench's native opt-out list and its existing tables.
    # Vanilla crafting tables belong to Cinematic Interactions; other supported
    # workbenches can still use Visual Workbench's persistent crafting inventory.
    path = 'data/visualworkbench/tags/block/unaltered_workbenches.json'
    workbenches = upstream('visual-workbench', path)
    if 'minecraft:crafting_table' not in workbenches['values']:
        workbenches['values'].append('minecraft:crafting_table')
    write_json(destination / path, workbenches)
    write_json(REPO / 'catalog/integration-data.json', {'sources': sources,
        'changes': ['Natural Treasures of the Dead spawns restricted to ocean and beach tags, with smaller groups and lower captain weights.',
                    'Structure raids, merchants, treasures and quest encounters remain available.',
                    'Create Deco placard ingredient uses the actual Minecraft 1.21.1 item key.',
                    'Visual Workbench native unaltered-workbench tag preserves vanilla crafting tables for Cinematic Interactions. Existing converted tables and their inventories are never replaced.'],
        'boundary': 'Claim protection and real combat tests remain required; this does not promise invulnerability.'})
    return str(destination)


if __name__ == '__main__':
    print(build())
