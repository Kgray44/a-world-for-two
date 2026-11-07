"""Select alternative texture packs in a closed, owned Prism client."""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from control_room.common import Layout, REPO, UserError, atomic_write, contained, digest, read_json, write_json
from control_room.graphics import Graphics
from control_room.presentation import closed
from control_room.storage import Storage


def select_text(text, base, overlay, alternatives):
    lines = text.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line.startswith('resourcePacks:')]
    if len(matches) > 1:
        raise UserError('Duplicate resource-pack settings; review options.txt')
    packs = json.loads(lines[matches[0]].split(':', 1)[1]) if matches else ['vanilla']
    if not isinstance(packs, list) or any(not isinstance(p, str) for p in packs):
        raise UserError('Invalid resource-pack selection')
    # Minecraft stores low priority first. Keep unrelated packs and their order.
    packs = [p for p in packs if p not in alternatives]
    packs.extend([base, overlay])
    value = 'resourcePacks:' + json.dumps(packs, ensure_ascii=False) + '\n'
    if matches:
        lines[matches[0]] = value
    else:
        if lines and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        lines.append(value)
    return ''.join(lines)


def fresh_options(lock):
    """Defaults for a new import only; never applied to an existing client."""
    text = 'renderDistance:8\nsimulationDistance:5\nmaxFps:60\nenableVsync:true\n'
    packs = {m['slug']: m['filename'] for m in lock['mods'] if m['kind'] == 'resourcepack'}
    selected = ['vanilla']
    if 'fresh-animations' in packs:
        selected.append('file/' + packs['fresh-animations'])
    if {'stylista', 'nautilus3d'} <= packs.keys():
        selected.extend('file/' + packs[key] for key in ('stylista', 'nautilus3d'))
    text += 'resourcePacks:' + json.dumps(selected) + '\n'
    if any(m.get('request') == 'diorama' for m in lock['mods']):
        text += ('key_key.diorama.open_map:key.keyboard.f8\n'
                 'key_key.diorama.new_waypoint:key.keyboard.f9\n'
                 'key_key.diorama.waypoints:key.keyboard.f10\n')
    return text


def material_text(text, settings):
    for key, value in settings.items():
        pattern = r'(?m)^' + re.escape(key) + r'=[^\r\n]*$'
        if len(re.findall(pattern, text)) > 1:
            raise UserError('Duplicate BSL setting: ' + key)
        if re.search(pattern, text):
            text = re.sub(pattern, lambda _: key + '=' + value, text)
        else:
            text += ('\n' if text and not text.endswith('\n') else '') + key + '=' + value + '\n'
    return text


def apply(home, client, preset, bsl_materials=False):
    layout = Layout(home)
    storage = Storage(layout)
    instance, _ = Graphics(layout, storage).client(client)
    closed(instance)
    config = read_json(REPO / 'catalog/texture-presets.json')
    if preset not in config['presets']:
        raise UserError('Choose enchanted-fantasy or soft-rounded')
    lock = read_json(REPO / 'catalog/lock.json')
    pins = {m['slug']: m for m in lock['mods'] if m['kind'] == 'resourcepack'}
    row = config['presets'][preset]
    names = {key: 'file/' + pins[key]['filename'] for p in config['presets'].values()
             for key in (p['base'], p['overlay'])}
    for slug in (row['base'], row['overlay']):
        pin = pins[slug]
        path = contained(instance, '.minecraft/resourcepacks/' + pin['filename'])
        if (not path.is_file() or path.is_symlink() or path.stat().st_size != pin['size']
                or any(digest(path, alg) != value for alg, value in pin['hashes'].items())):
            raise UserError('Install the exact pinned resource pack first: ' + pin['filename'])
    options = contained(instance, '.minecraft/options.txt')
    if options.is_symlink() or options.is_junction() or (options.exists() and options.stat().st_size > 1024 * 1024):
        raise UserError('Unsafe or oversized options.txt')
    before = options.read_bytes() if options.exists() else b''
    text = before.decode('utf-8')
    updated = select_text(text, names[row['base']], names[row['overlay']], set(names.values()))
    storage.reserve(4 * 1024 * 1024, instance)
    shader_receipt = None
    if bsl_materials:
        shader = next(m for m in lock['mods'] if m['slug'] == config['shader'])
        target = contained(instance, '.minecraft/shaderpacks/' + shader['filename'] + '.txt')
        if target.exists() and target.stat().st_size > 65536:
            raise UserError('BSL options exceed the editing limit')
        old_shader = target.read_bytes() if target.exists() else b''
        shader_text = material_text(old_shader.decode('utf-8'), config['bsl_settings'])
        iris = contained(instance, '.minecraft/config/iris.properties')
        shader_receipt = Graphics(layout, storage).apply(client, config['shader'], digest(iris) if iris.exists() else None)
        previous = contained(instance, 'awft-graphics-history/' + str(time.time_ns()) + '-bsl.txt')
        atomic_write(previous, old_shader)
        if (target.read_bytes() if target.exists() else b'') != old_shader:
            raise UserError('BSL settings changed during selection; backup preserved')
        atomic_write(target, shader_text)
        shader_receipt['previous_material_settings'] = str(previous)
    history = contained(instance, 'awft-graphics-history/' + str(time.time_ns()) + '-options.txt')
    atomic_write(history, before)
    # Refuse concurrent changes immediately before the write.
    closed(instance)
    if (options.read_bytes() if options.exists() else b'') != before:
        raise UserError('Client settings changed during selection; preserved the backup')
    atomic_write(options, updated)
    receipt = {'preset': preset, 'previous': str(history), 'revision': digest(options),
               'status': 'Selected for next launch; in-game rendering unverified',
               'shader': shader_receipt or 'Existing shader and Distant Horizons settings preserved'}
    write_json(instance / 'awft-texture-preset.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--client', required=True)
    parser.add_argument('--bsl-materials', action='store_true', help='Explicitly select pinned BSL and apply the saved restrained LabPBR settings')
    parser.add_argument('preset', choices=('enchanted-fantasy', 'soft-rounded'))
    args = parser.parse_args()
    print(json.dumps(apply(args.home, args.client, args.preset, args.bsl_materials), indent=2))


if __name__ == '__main__':
    main()
