"""Prepare existing Character Studio Save drafts from existing LIFE recipes.

No HTTP, game commands, world reads/writes, runtime installation or spawning.
The master lane verifies native admission/UUIDs before submitting these drafts
through the existing Save endpoint, then Apply. A draft is not a live binding.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import uuid

from control_room.characters import validate_profile
from control_room.common import UserError
from living_world.cast import HABITATS, ROLES, TARGETS


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2) + '\n').encode('utf8')


def read(path, cap):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > cap:
        raise UserError('A bounded ordinary source file is required')
    raw = path.read_bytes()
    if len(raw) > cap:
        raise UserError('Source grew beyond its bound')
    return json.loads(raw), {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def point(value):
    return (isinstance(value, list) and len(value) == 3 and
            all(type(x) in (int, float) and math.isfinite(x) and abs(x) <= 30000000 for x in value))


def prepare(registry, recipes, placements=None):
    config = registry.get('config', {})
    if config.get('format') != 'awft-living-world:1':
        raise UserError('Use the current actual Control Room registry')
    configured = config.get('characters', [])
    profiles = {p['id']: p for p in configured}
    if len(profiles) != len(configured) or not ROLES.keys() <= profiles.keys():
        raise UserError('All ten existing configured identities must be retained, without duplicate IDs')
    if placements is not None and placements.get('format') != 'awft-tortuga-cast-sites:1':
        raise UserError('Use the explicit source city cast-site proposal')
    premises = {p['character_id']: p for p in (placements or {}).get('sites', [])}
    members, identities, beds, jobs, worlds = {}, set(), set(), set(), set()
    for recipe in recipes:
        if recipe.get('format') not in ('awft-habitat-life-recipe:3', 'awft-habitat-life-recipe:4') or recipe.get('copied_entity_NBT') is not False:
            raise UserError('Use existing native LIFE v3/v4 recipes without copied NBT')
        if recipe.get('dimension') != 'minecraft:overworld':
            raise UserError('This cast uses the actual overworld town sites')
        worlds.add((recipe['world_path'], str(recipe['seed']), str(uuid.UUID(recipe['population_namespace']))))
        rows = recipe.get('members', [])
        if not 1 <= len(rows) <= (64 if recipe['format'].endswith(':4') else 16):
            raise UserError('Retain existing native cohort bounds')
        for member in rows:
            ident = str(uuid.UUID(member['uuid']))
            if ident in identities:
                raise UserError('A native UUID occurs in more than one supplied recipe')
            identities.add(ident)
            group = member.get('source_group_id', '')
            if not group.startswith('character-'):
                continue
            key = group.removeprefix('character-')
            if key not in ROLES or key in members:
                raise UserError('Use one existing configured character per explicit character-<id> group')
            site = member.get('habitat', {})
            if (member.get('entity') != 'minecraft:villager' or member.get('native_class') != 'net.minecraft.world.entity.npc.Villager'
                    or member.get('native_MobCategory') != 'misc' or site.get('kind') != 'HOME' or not member.get('town_site')):
                raise UserError('A named figure needs an existing native villager HOME/town recipe')
            if profiles[key].get('kind') != 'villager' or profiles[key].get('entity_type') != 'minecraft:villager':
                raise UserError('Preserve an owner change to this character\'s entity kind')
            if not all(point(site.get(k)) for k in ('bed', 'job', 'roof')) or not point(member.get('feet')):
                raise UserError('Real HOME, job, roof and resident positions are required')
            bed, job = tuple(site['bed']), tuple(site['job'])
            if bed == job or bed in beds or job in jobs:
                raise UserError('Do not share or invent the ten residents\' bed/job sites')
            for route in ('bed_path', 'job_path'):
                if not 1 <= len(site.get(route, [])) <= 64 or not all(point(p) for p in site[route]):
                    raise UserError('Retain the existing complete native bed and job routes')
            beds.add(bed); jobs.add(job)
            previous = profiles[key].get('entity_uuid')
            if previous and previous != ident:
                raise UserError('Preserve an existing character binding; do not silently replace its resident')
            if any(p.get('entity_uuid') == ident and p['id'] != key for p in configured):
                raise UserError('This native UUID is already bound to another character')
            members[key] = member
    if len(worlds) > 1:
        raise UserError('Recipes must use the same actual world and retained population namespace')
    drafts, roles = {}, []
    for key, source in ROLES.items():
        role, room, profession, station, joke = source
        row = {'id': key, 'name': profiles[key]['name'], 'authored_role': profiles[key].get('role') or role,
               'room_requirement': room, 'expected_native_profession': profession, 'required_job_block': station,
               'native_HOME_job_claims_behavior_and_room_acceptance': 'PENDING'}
        if key in members:
            member = members[key]
            p = deepcopy(profiles[key])
            p['entity_uuid'] = str(uuid.UUID(member['uuid']))
            if key in premises:
                proposal = premises[key]
                if proposal['town_site'] != member['town_site'] or proposal['feet'] != member['feet']:
                    raise UserError('Source premise must match this exact native LIFE member')
                changes = proposal['profile_edits']
                for field in ('district', 'home_location'):
                    if p[field] != changes[field]['before']:
                        raise UserError('Owner changed the premise/district since staging; regenerate the site proposal')
                    p[field] = changes[field]['after']
                row.update(profile_edits=changes, visiting_role=proposal['visiting_role'])
            # Assigned source position is deliberately not current native telemetry.
            p['location'] = dict(zip(('x', 'y', 'z'), member['feet']), dimension='minecraft:overworld', measured_at=None)
            lines = p.setdefault('dialogue', {}).setdefault('lines', {})
            if not lines.get('jokes'):
                lines['jokes'] = [joke]
            for category in ('nighttime', 'weather', 'nearby_player'):
                if not lines.get(category):
                    lines[category] = [joke]
            # Existing model, AI/consent settings, speech options, lore and authored
            # dialogue are preserved. This operation never enables paid requests.
            p = validate_profile(p)
            drafts[key] = {'format': 'awft-character:1', 'character': p}
            row.update(uuid=p['entity_uuid'], town_site=member['town_site'], bed=member['habitat']['bed'], job=member['habitat']['job'])
        roles.append(row)
    report = {'source_only': True, 'configured_cast': roles, 'draft_ids': sorted(drafts),
              'pending_site_ids': sorted(ROLES.keys() - members.keys()), 'native_entities_spawned': 0,
              'runtime_installed': False, 'provider_request_made': False,
              'population_total_targets_including_retained_intents': TARGETS, 'habitat_requirements': HABITATS,
              'target_total': sum(TARGETS.values()),
              'next': 'Master verifies native LIFE admission and exact UUID/type; fetches the current Studio revision for each existing Save, then Apply and exact native hash acknowledgement. Do not use Import, which intentionally clears bindings.'}
    return drafts, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--recipe', type=Path, action='append', default=[])
    parser.add_argument('--sites', type=Path, help='Explicit city premise/visiting-role edits, kept in the source report')
    parser.add_argument('--output', type=Path, required=True, help='New source-only output directory, never dashboard/config/world')
    args = parser.parse_args()
    out = args.output.absolute()
    if out.exists() or any(part.casefold() in ('dashboard', 'server', 'config', 'world', 'worlds', 'packwiz') for part in out.parts):
        raise UserError('Choose a new source-only staging directory')
    registry, registry_ref = read(args.registry, 8 * 1024**2)
    if len(args.recipe) > 16:
        raise UserError('Use at most sixteen existing finite LIFE recipes')
    recipes, refs = [], []
    for path in args.recipe:
        value, ref = read(path, 16 * 1024**2); recipes.append(value); refs.append(ref)
    placements, placement_ref = read(args.sites, 1024**2) if args.sites else (None, None)
    drafts, report = prepare(registry, recipes, placements)
    if placement_ref:
        report['premise_proposal_source'] = placement_ref
    report.update(registry_source=registry_ref, recipe_sources=refs)
    files = {key + '.json': encoded(value) for key, value in drafts.items()}
    files['deployment.json'] = encoded(report)
    if sum(map(len, files.values())) > 1024**2:
        raise UserError('Cast staging exceeds its one MiB bound')
    out.mkdir(parents=True)
    for name, raw in files.items():
        (out / name).write_bytes(raw)
    print(json.dumps({'source_only': True, 'drafts': len(drafts), 'pending_sites': len(report['pending_site_ids']), 'output': str(out)}))


if __name__ == '__main__':
    main()
