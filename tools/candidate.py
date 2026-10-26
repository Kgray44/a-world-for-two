"""Materialize the reviewed source repairs and additions as one candidate lock."""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

from control_room.common import Layout, REPO, digest, read_json, utcnow, write_json
from control_room.pack import generate_pack
from control_room.storage import Storage
from .build_bridge import build as build_bridge
from .build_presentation import build as build_presentation
from .weather_patch import build as build_weather, PATCH_VERSION
from .seedgen_policy import apply as seedgen_policy


def prepare(home):
    layout = Layout(home)
    storage = Storage(layout)
    storage.reserve(64 * 1024 * 1024)
    storage.reserve(4 * 1024 * 1024, REPO)
    directory = layout.staging / ('candidate-build-' + str(time.time_ns()))
    directory.mkdir()
    previous = read_json(REPO / 'catalog/lock.json')
    selection = read_json(REPO / 'catalog/selection.json')
    research = read_json(REPO / 'catalog/build-inputs/archaeology-resolved.json')
    author = read_json(REPO / 'catalog/build-inputs/ldtteam-candidates.json')['mods']
    shaders = read_json(REPO / 'catalog/build-inputs/shader-resolved.json', {'mods': [], 'choices': []})
    shader_projects = {m['project_id'] for m in shaders['mods']}
    items = [m for m in research['mods'] if m['project_id'] not in shader_projects] + shaders['mods']
    weather = next(m for m in items if m['slug'] == 'advanced-weather')
    base = weather.get('upstream_artifact', weather)
    artifact = directory / ('advancedweather-' + PATCH_VERSION + '.jar')
    patched, provenance = build_weather(layout.caches / 'mods' / base['filename'], artifact, base, storage, layout.server / 'libraries')
    patched['url'] = 'https://github.com/Kgray44/a-world-for-two/releases/download/compat-0.1.0/' + artifact.name
    patched['upstream_artifact'] = base
    patched['repair'] = provenance
    bridge = build_bridge(layout.home, directory / 'awft-control-bridge-0.5.0.jar', storage)
    presentation = build_presentation(layout.home, directory / 'awft-client-presentation-0.2.1.jar', storage)
    gadget_file = layout.caches / 'mods/buildinggadgets2-21.1.1.jar'
    gadgets = {'project_id':'curseforge:298187', 'slug':'building-gadgets-2', 'name':'Building Gadgets 2',
        'version_id':'curseforge:9310471', 'version':'21.1.1', 'provider':'curseforge', 'release_type':'release',
        'curseforge_project':298187, 'curseforge_file':9310471, 'filename':gadget_file.name,
        'url':'https://www.curseforge.com/minecraft/mc-mods/building-gadgets/download/9310471',
        'size':gadget_file.stat().st_size, 'hashes':{'sha256':digest(gadget_file)}, 'side':'both', 'kind':'mod',
        'request':'building-gadgets-2', 'world_sensitive':True, 'optional':False, 'default':True, 'dependencies':[],
        'license':{'id':'MIT'}, 'source':'https://www.curseforge.com/minecraft/mc-mods/building-gadgets/files/9310471',
        'selection_reason':'Official NeoForge 1.21.1 maintenance release fixes connected-area handling and gadget menus. Acquired by the exact Curse Maven coordinate published on its official file page; native and gameplay checks still required.',
        'status':'Integrated but awaiting runtime validation', 'validation':{'metadata':'pass','jar':'pending','runtime':'not run'}}
    owned = [bridge, presentation]
    for item in [patched, *owned]:
        source = directory / item['filename']
        cached = layout.caches / 'mods' / item['filename']
        if cached.exists() and digest(cached) != digest(source):
            raise ValueError('An immutable candidate filename already contains different bytes: ' + item['filename'])
        if not cached.exists():
            shutil.copy2(source, cached)
    replacements = {m['slug']:m for m in [patched, *owned, *author, gadgets]}
    items = [m for m in items if m['slug'] not in replacements] + list(replacements.values())
    items = seedgen_policy(items, selection, layout.caches / 'mods')
    for m in items:
        if m['slug'] == 'yacl':
            m['side'] = 'both'
    version = '0.1.0-candidate.12'
    existing_projects = {m['project'] for m in selection['mods']}
    for choice in research['choices'] + shaders['choices']:
        if choice['project'] not in existing_projects:
            selection['mods'].append(choice)
            existing_projects.add(choice['project'])
    artifacts = {m['slug']:m for m in selection['artifacts']}
    artifacts.update({m['slug']:m for m in [*owned, *author, gadgets]})
    selection.update(version=version, artifacts=list(artifacts.values()), repairs=[patched])
    write_json(REPO / 'evidence/history' / ('lock-' + str(time.time_ns()) + '.json'), previous)
    lock = previous | {'version':version, 'generated':utcnow(), 'mods':sorted(items,key=lambda m:m['name'].lower()),
        'validation':'Native checks, complete candidate startup and interactive multiplayer acceptance pending'}
    write_json(REPO / 'catalog/selection.json', selection)
    write_json(REPO / 'catalog/lock.json', lock)
    write_json(directory / 'build.json', {'at':utcnow(),'weather':provenance,'owned':owned,'source_hashes':{
        p.relative_to(REPO).as_posix():digest(p) for folder in ['compat/control-bridge','compat/client-presentation','compat/advanced-weather'] for p in (REPO/folder).rglob('*') if p.is_file()}})
    result = {'version':version, 'entries':len(items), 'mods':sum(m['kind']=='mod' for m in items),
        'enabled_mods':sum(m['kind']=='mod' and not(m.get('optional') and not m.get('default',True)) for m in items),
        'pack_sha256':generate_pack(REPO/'packwiz',lock), 'build_directory':str(directory)}
    print(result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    prepare(parser.parse_args().home)
