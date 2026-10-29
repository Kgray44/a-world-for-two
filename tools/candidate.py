"""Materialize the reviewed source repairs and additions as one candidate lock."""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

from control_room.common import Layout, REPO, digest, read_json, utcnow, write_json
from control_room.pack import generate_pack, validate_pack
from control_room.storage import Storage
from .build_bridge import build as build_bridge, BRIDGE_VERSION
from .build_presentation import build as build_presentation, PRESENTATION_VERSION
from .weather_patch import build as build_weather, PATCH_VERSION
from .seedgen_policy import apply as seedgen_policy

VERSION = '0.1.0-candidate.65'


def prepare_owned(home):
    """Replace only the two owned helpers, preserving every gameplay artifact."""
    layout=Layout(home);storage=Storage(layout)
    storage.reserve(64*1024**2)
    storage.reserve(8*1024**2,REPO)
    previous=read_json(REPO/'catalog/lock.json')
    if previous['version']==VERSION or validate_pack(REPO/'packwiz',previous):
        raise ValueError('A valid previous immutable candidate is required')
    directory=layout.staging/('candidate-owned-build-'+str(time.time_ns()));directory.mkdir()
    bridge=build_bridge(layout.home,directory/('awft-control-bridge-'+BRIDGE_VERSION+'.jar'),storage)
    presentation=build_presentation(layout.home,directory/('awft-client-presentation-'+PRESENTATION_VERSION+'.jar'),storage)
    replacements={m['slug']:m for m in (bridge,presentation)}
    for artifact in replacements.values():
        source=directory/artifact['filename'];cached=layout.caches/'mods'/artifact['filename']
        if cached.exists() and digest(cached)!=artifact['hashes']['sha256']:
            raise ValueError('An immutable owned artifact filename already contains different bytes')
        if not cached.exists():shutil.copy2(source,cached)
    if any(sum(m['slug']==slug for m in previous['mods'])!=1 for slug in replacements):
        raise ValueError('Each owned helper must have exactly one predecessor')
    items=[replacements.get(m['slug'],m) for m in previous['mods']]
    selection=read_json(REPO/'catalog/selection.json')
    selection.update(version=VERSION,artifacts=[replacements.get(m['slug'],m) for m in selection['artifacts']])
    history=REPO/'evidence/history'/('lock-'+str(time.time_ns())+'.json')
    write_json(history,previous)
    lock=previous|{'version':VERSION,'generated':utcnow(),'mods':items,
        'validation':'Gameplay artifact pins preserved; owned helper native validation is recorded separately'}
    write_json(REPO/'catalog/selection.json',selection);write_json(REPO/'catalog/lock.json',lock)
    result={'version':VERSION,'entries':len(items),'mods':sum(m['kind']=='mod' for m in items),
        'pack_sha256':generate_pack(REPO/'packwiz',lock),'build_directory':str(directory),
        'previous_lock_sha256':digest(history),'owned':[bridge,presentation],
        'preserved_gameplay_pins':True,
        'source_hashes':{p.relative_to(REPO).as_posix():digest(p)
            for name in ('compat/control-bridge','compat/client-presentation')
            for p in (REPO/name).rglob('*') if p.is_file()}}
    write_json(directory/'build.json',result)
    print(result)
    return result


def prepare_bridge(home, mapping_artifact=None, chain_research=None, zipline_configs=None, include_presentation=False):
    """Build the owned bridge and optional exact mapping repair, retaining other pins."""
    layout=Layout(home);storage=Storage(layout)
    storage.reserve(32*1024**2)
    storage.reserve(4*1024**2,REPO)
    previous=read_json(REPO/'catalog/lock.json')
    if previous['version']==VERSION or validate_pack(REPO/'packwiz',previous):
        raise ValueError('A valid previous immutable candidate is required')
    config_inputs=[]
    if zipline_configs is not None:
        root=Path(zipline_configs).resolve()
        if root!=(REPO/'compat/proposals/zipline-config44').resolve() or root.is_symlink():
            raise ValueError('Only the reviewed bounded44 zipline configuration source is admitted')
        for name,pin in [('connectiblechains.json','99176d18c26709e34457f840f92a024d70e65f34e6a7b6bd9320d4efe7e3f003'),
                         ('zipline.json','fabf9030eb8e93c5d5d4b038940b44ae602e11e54fcdd4e275387d1b26f07e12')]:
            source=root/name;target=REPO/'packwiz/config'/name
            if (not source.is_file() or source.is_symlink() or not 0<source.stat().st_size<=16384
                    or digest(source)!=pin or target.exists() or target.is_symlink()):
                raise ValueError('Preserve existing configuration; exact new reviewed44 source is required: '+name)
            config_inputs.append((source,target,pin))
    chain=None
    if chain_research is not None:
        from control_room.pack import validate_graph, validate_jars
        research=Path(chain_research).resolve()
        source=research/'connectiblechains-2.4.4+1.21.1-neoforge.jar'
        chain=read_json(research/'PROPOSED-artifact-not-installed.json')
        if (not research.is_relative_to(layout.staging) or research.is_symlink()
                or chain.get('project_id')!='5pzBXDS3' or chain.get('slug')!='reconnectible-chains'
                or chain.get('version_id')!='e4yVoAvP' or chain.get('version')!='2.4.4+1.21.1-neoforge'
                or chain.get('side')!='both' or chain.get('kind')!='mod' or chain.get('optional') is not False
                or chain.get('filename')!=source.name or chain.get('size')!=293575
                or source.stat().st_size!=293575 or source.is_symlink()
                or digest(source)!='70d9f048e6f358c83b2d35f8a69000ec7827023efcc6d3b75346b4e34238bbd0'
                or chain.get('hashes',{}).get('sha512')!='c09a3a354a26ce0dc511c2364332975222fae8515101f524de5e724f3a191eb75ffb4f381b8c78907f885d7a7e86f1ce7b883d56921fb5f31709466446efe00a'
                or any(m['slug']=='reconnectible-chains' for m in previous['mods'])):
            raise ValueError('Only the exact reviewed new NeoForge Reconnectible Chains backend is admitted')
        chain['hashes']['sha256']=digest(source)
        target=layout.caches/'mods'/source.name
        if target.exists() and digest(target)!=digest(source):raise ValueError('Immutable chain cache filename differs')
        if not target.exists():shutil.copy2(source,target)
        prospective=previous|{'mods':previous['mods']+[chain]}
        errors=validate_graph(prospective['mods'])+validate_jars(prospective,layout.caches/'mods')['errors']
        if errors:raise ValueError('Native chain dependency/JAR validation failed: '+str(errors))
    directory=layout.staging/('candidate-bridge-build-'+str(time.time_ns()));directory.mkdir()
    bridge=build_bridge(layout.home,directory/('awft-control-bridge-'+BRIDGE_VERSION+'.jar'),storage)
    cached=layout.caches/'mods'/bridge['filename']
    if cached.exists() and digest(cached)!=bridge['hashes']['sha256']:
        raise ValueError('An immutable bridge filename already contains different bytes')
    if not cached.exists():shutil.copy2(directory/bridge['filename'],cached)
    presentation=None
    if include_presentation:
        prior=next(m for m in previous['mods'] if m['slug']=='awft-client-presentation')
        if prior['version']==PRESENTATION_VERSION:
            raise ValueError('A new immutable presentation version is required')
        path=directory/('awft-client-presentation-'+PRESENTATION_VERSION+'.jar')
        presentation=build_presentation(layout.home,path,storage)
        target=layout.caches/'mods'/presentation['filename']
        if target.exists() and digest(target)!=presentation['hashes']['sha256']:
            raise ValueError('Immutable presentation filename contains different bytes')
        if not target.exists():shutil.copy2(path,target)
    # Git publishes LF text. The installed Tectonic config already has these
    # exact LF bytes; preserve all settings while making the source hash portable.
    tectonic=REPO/'packwiz/config/tectonic.json'
    raw=tectonic.read_bytes();normalized=raw.replace(b'\r\n',b'\n')
    normalizations=[]
    if raw!=normalized:
        if digest(tectonic)!='3b30742af26922774c5efe8ad6f85e7f4eb8e61ee4261533c2d060e1d1d9a5d0':
            raise ValueError('Unreviewed Tectonic bytes cannot change through a bridge-only candidate')
        original=directory/'tectonic-before-line-ending-normalization.json'
        original.write_bytes(raw)
        tectonic.write_bytes(normalized)
        if digest(tectonic)!='9ca01c0e5f109c517d2ebc025d933ca30c7c9f5010019b67527b061ecb8869d5':
            raise ValueError('Tectonic normalization differs from its reviewed LF bytes')
        normalizations.append({'file':'config/tectonic.json','before_sha256':digest(original),
            'after_sha256':digest(tectonic),'change':'CRLF to LF only; all non-line-ending bytes identical'})
    replacements={'awft-control-bridge':bridge}
    if presentation is not None:replacements['awft-client-presentation']=presentation
    if mapping_artifact is not None:
        mapping_artifact=Path(mapping_artifact).resolve()
        expected='cd5f5a0d41f02d1c720b0ce3f603f0cc3c3f92db02aa8226565b4e394fbc7ef4'
        if (not mapping_artifact.is_relative_to(layout.staging)
                or mapping_artifact.name!='maphorizons-1.1.0-awft.2.jar'
                or mapping_artifact.stat().st_size!=121569 or digest(mapping_artifact)!=expected):
            raise ValueError('Only the reviewed, bounded MapHorizons awft.2 build is admitted')
        prior=next(m for m in previous['mods'] if m['slug']=='maphorizons')
        if prior['hashes'].get('sha256')!='da36054b9d59083481bfe9c946d17a2f0f87705a6d883718b26351848d40ff93' or prior['license'].get('id')!='MIT':
            raise ValueError('The exact reviewed MIT MapHorizons predecessor is required')
        mapping=prior|{'version_id':'1.1.0+6c80ad5+awft.2','filename':mapping_artifact.name,
            'url':'https://github.com/Kgray44/a-world-for-two/releases/download/compat-0.1.0/'+mapping_artifact.name,
            'size':121569,'hashes':{'sha256':expected},
            'selection_reason':'Original MIT interoperability repair for native DH coarse LOD lookup, read-only shaded SQLite and refresh races. Actual Xaero appearance, authority and SeedGen data provenance remain native test gates.',
            'validation':{'metadata':'pass','jar':'pinned API compilation and 76 helper checks pass','runtime':'not run'},
            'status':'Experimental native map validation pending'}
        target=layout.caches/'mods'/mapping_artifact.name
        if target.exists() and digest(target)!=expected:raise ValueError('Immutable MapHorizons cache filename differs')
        if not target.exists():shutil.copy2(mapping_artifact,target)
        replacements['maphorizons']=mapping
    selection=read_json(REPO/'catalog/selection.json')
    selection.update(version=VERSION,artifacts=[replacements.get(m['slug'],m) for m in selection['artifacts']])
    items=[replacements.get(m['slug'],m) for m in previous['mods']]
    if chain is not None:
        items.append(chain)
        selection['mods'].append({'request':'reconnectible-chains','project':'reconnectible-chains',
            'version':'e4yVoAvP','side':'both','world_sensitive':True,
            'reason':chain['selection_reason']})
    if sum(m['slug']=='awft-control-bridge' for m in items)!=1:
        raise ValueError('Exactly one owned bridge must already exist')
    lock=previous|{'version':VERSION,'generated':utcnow(),'mods':items,
        'validation':'Explicitly reviewed helper/mapping changes and optional exact zipline cable addition only; native restart and integration checks pending'}
    for source,target,pin in config_inputs:
        raw=source.read_bytes()
        if digest(source)!=pin:raise ValueError('Reviewed configuration source changed during build')
        with target.open('xb') as output:output.write(raw)
    history=REPO/'evidence/history'/('lock-'+str(time.time_ns())+'.json')
    write_json(history,previous)
    write_json(REPO/'catalog/selection.json',selection)
    write_json(REPO/'catalog/lock.json',lock)
    result={'version':VERSION,'entries':len(items),'mods':sum(m['kind']=='mod' for m in items),
        'enabled_mods':sum(m['kind']=='mod' and not(m.get('optional') and not m.get('default',True)) for m in items),
        'pack_sha256':generate_pack(REPO/'packwiz',lock),'build_directory':str(directory),
        'previous_lock_sha256':digest(history),
        'owned_bridge':bridge,'preserved_gameplay_pins':mapping_artifact is None and chain is None,
        'owned_presentation':replacements.get('awft-client-presentation'),
        'reviewed_zipline_backend_addition':chain,
        'reviewed_zipline_config_additions':[{'file':target.relative_to(REPO).as_posix(),'sha256':pin} for source,target,pin in config_inputs],
        'reviewed_mapping_change':replacements.get('maphorizons'),'preserved_other_gameplay_pins':True,
        'byte_only_config_normalizations':normalizations,
        'source_hashes':{p.relative_to(REPO).as_posix():digest(p) for group in ('src','resources')
            for p in (REPO/'compat/control-bridge'/group).rglob('*') if p.is_file()},
        'presentation_source_hashes':{p.relative_to(REPO).as_posix():digest(p) for group in ('src','resources')
            for p in (REPO/'compat/client-presentation'/group).rglob('*') if p.is_file()},
        'noncompiled_proposals_excluded':True}
    write_json(directory/'build.json',result)
    print(result)
    return result

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
    bridge = build_bridge(layout.home, directory / ('awft-control-bridge-'+BRIDGE_VERSION+'.jar'), storage)
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
    version = VERSION
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
    parser.add_argument('--bridge-only',action='store_true')
    parser.add_argument('--owned-only',action='store_true')
    parser.add_argument('--mapping-jar',type=Path)
    parser.add_argument('--chain-research',type=Path)
    parser.add_argument('--zipline-configs',type=Path)
    parser.add_argument('--include-presentation',action='store_true')
    args=parser.parse_args()
    if args.mapping_jar and (not args.bridge_only or args.owned_only):
        parser.error('--mapping-jar requires the bridge-only, explicitly reviewed candidate path')
    if args.chain_research and (not args.bridge_only or args.owned_only):
        parser.error('--chain-research requires the bridge-only, explicitly reviewed candidate path')
    if args.zipline_configs and (not args.bridge_only or args.owned_only):
        parser.error('--zipline-configs requires the bridge-only, explicitly reviewed candidate path')
    if args.include_presentation and (not args.bridge_only or args.owned_only):
        parser.error('--include-presentation requires the explicitly reviewed bridge candidate path')
    if args.bridge_only:prepare_bridge(args.home,args.mapping_jar,args.chain_research,args.zipline_configs,args.include_presentation)
    else:(prepare_owned if args.owned_only else prepare)(args.home)
