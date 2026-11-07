"""Export exact upstream configuration into a new, owned integration bundle.

This module never installs JARs, sends Minecraft commands, accepts an EULA or
writes the canonical pack. District matching requires the Living World adapter.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from control_room.common import REPO, UserError

PROPOSAL = REPO / 'proposals/living-world/mods'
MAX_BUNDLE_BYTES = 2 * 1024 * 1024
MAX_ALLOCATION_BYTES = MAX_BUNDLE_BYTES + 1024 * 1024  # filesystem metadata and slack
TOKEN = re.compile(r'^[a-z][a-z0-9_-]{0,63}$')


def inventory():
    return json.loads((PROPOSAL / 'inventory.json').read_text(encoding='utf-8'))


def packwiz_entry(mod, optional=False):
    """Render a content-pinned metafile; held artifacts are never exportable."""
    if mod.get('status') != 'pinned-proposal-awaiting-native-validation':
        raise UserError('This mod is held or is an existing pack entry')
    text = '\n'.join([
        'name = ' + json.dumps(mod['name']),
        'filename = ' + json.dumps(mod['filename']),
        'side = "both"', '', '[download]',
        'url = ' + json.dumps(mod['url']), 'hash-format = "sha512"',
        'hash = ' + json.dumps(mod['hashes']['sha512']), '',
    ])
    if optional:
        text += '[option]\noptional = true\ndefault = false\ndescription = "Optional NPC speech transport; owner setup and native tests required"\n'
    if mod.get('version_id'):
        text += '\n[update.modrinth]\nmod-id = ' + json.dumps(mod['project_id']) + '\nversion = ' + json.dumps(mod['version_id']) + '\n'
    elif mod.get('file_id'):
        text += '\n[update.curseforge]\nfile-id = ' + str(mod['file_id']) + '\nproject-id = ' + str(mod['project_id']) + '\n'
    return text


def verify_artifact(path, mod):
    """Verify a bounded author download without extracting or executing it."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size != mod['size']:
        raise UserError('Artifact missing, linked or wrong size: ' + mod['id'])
    if path.stat().st_size > 16 * 1024 * 1024:
        raise UserError('Artifact exceeds bounded verification size')
    digest = hashlib.sha512()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != mod['hashes']['sha512']:
        raise UserError('Artifact hash differs: ' + mod['id'])
    return {'id': mod['id'], 'size': mod['size'], 'sha512': digest.hexdigest(), 'verified': True}


def chatting_config():
    # Actual 1.1.0 ModConfig fields checked against the pinned NeoForge artifact.
    return {'masterEnabled': True, 'language': 'en_us', 'builtInDialogue': False,
            'disabledCategories': ['popculture', 'insider', 'realworld'],
            'radius': 16.0, 'speakIntervalTicks': 140, 'portalScanRadius': 0,
            'frequencyPreset': 'quiet', 'villagerCooldownSeconds': 90,
            'speakChance': 0.15, 'maxMessagesPerPlayerPerMinute': 3,
            'chanceFactorNight': 0.2, 'conversationsEnabled': True,
            'conversationChance': 0.08, 'conversationRadius': 5.0,
            'pairCooldownSeconds': 200, 'conversationLineDelayTicks': 60,
            'bubblesEnabled': True, 'bubbleLifetimeTicks': 100,
            'chatMessagesEnabled': False, 'reactionsEnabled': True,
            'reactionCooldownTicks': 100, 'tradeReactionChance': 0.1}


def smart_config():
    # No model or credential is selected. Upstream isConfigured remains false.
    return '''# Living World proposal: private provider configuration stays server-side.
[proximity]
enabled = true
hearingRadius = 8.0
responseRadius = 16.0
activationMode = "PREFIX"
chatPrefix = "!"
requirePrefix = true
ignorePlayerToPlayerChat = true

[display]
mode = "CHAT"
speechBubbles = true
cancelGlobalChatWhenTalking = false

[privacy]
requirePlayerOptIn = true

[ai]
provider = "CUSTOM"
apiBaseUrl = "https://api.openai.com/v1"
endpointMode = "AUTO"
model = ""
apiKey = ""
maxReplyChars = 180
maxTokens = 128
playerCooldownMs = 10000
globalRequestsPerMinute = 12
maxConcurrent = 2
thinkingDelayMinTicks = 10
thinkingDelayMaxTicks = 20

[persona]
allowPlayersEditPersona = false

[voice]
enabled = false
volume = 0.6
range = 16.0
fallbackToText = true

[requests]
enabled = false
maxActive = 1
cooldownMinutes = 20
reputationReward = 0
'''


def district_dialogue(districts):
    """Map the editable district catalog to Chatting Villagers' JSON arrays.

    The upstream state matcher uses OR. Use exactly one district state marker;
    never append a district token to another upstream state condition.
    """
    files = {}
    if not isinstance(districts, list) or len(districts) > 16:
        raise UserError('Use at most 16 dialogue districts')
    seen = set()
    for district in districts:
        if not isinstance(district, dict):
            raise UserError('A dialogue district must be an object')
        ident = district.get('id', '')
        if not isinstance(ident, str) or not TOKEN.fullmatch(ident) or ident in seen:
            raise UserError('Invalid dialogue district identifier')
        seen.add(ident)
        rows = []
        dialogue = district.get('dialogue', {})
        if not isinstance(dialogue, dict) or len(dialogue) > 30:
            raise UserError('Dialogue categories exceed bounds')
        for category, lines in dialogue.items():
            if not isinstance(category, str) or not TOKEN.fullmatch(category) or not isinstance(lines, list) or len(lines) > 100:
                raise UserError('Invalid dialogue category or line count')
            for index, line in enumerate(lines):
                if not isinstance(line, str) or not line.strip() or len(line) > 240 or any(ord(c) < 32 for c in line):
                    raise UserError('Dialogue needs short printable lines')
                conditions = {'state': ['awft_district_' + ident]}
                if category in ('night', 'nighttime'):
                    conditions['timeOfDay'] = ['night']
                elif category in ('weather', 'rain'):
                    conditions['weather'] = ['rain', 'thunder']
                elif category == 'morning':
                    conditions['timeOfDay'] = ['morning']
                rows.append({'id': 'awft_' + ident + '_' + category + '_' + str(index),
                             'type': 'solo', 'category': 'awft_' + category,
                             'conditions': conditions, 'weight': 1.0, 'text': line.strip()})
        if len(rows) > 1000:
            raise UserError('District dialogue exceeds 1000 lines')
        files['config/chattingvillagers/dialogue/en_us/awft_' + ident + '.json'] = rows
    return files


def bundle_files(districts):
    files = {'config/chattingvillagers.json': json.dumps(chatting_config(), indent=2) + '\n',
             'config/smartvillagers/config.toml': smart_config()}
    for name, rows in district_dialogue(districts).items():
        files[name] = json.dumps(rows, ensure_ascii=False, indent=2) + '\n'
    for mod in inventory()['mods']:
        if mod['status'] == 'pinned-proposal-awaiting-native-validation':
            files['mods/' + mod['id'] + '.pw.toml'] = packwiz_entry(mod, optional=not mod['default_enabled'])
    if sum(len(value.encode('utf-8')) for value in files.values()) > MAX_BUNDLE_BYTES:
        raise UserError('Integration bundle exceeds its finite allocation')
    return files


def reserve_allocation(destination):
    if os.name != 'nt':
        return
    drive = Path(destination).drive.upper()
    guard = Path(os.environ.get('LOCALAPPDATA', '')) / 'AeroStorageWatch/ReserveGuard.ps1'
    if not guard.is_file():
        raise UserError('The required AERO storage reserve guard is unavailable')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-File', str(guard),
                             '-EstimatedCBytes', str(MAX_ALLOCATION_BYTES if drive == 'C:' else 0),
                             '-EstimatedDBytes', str(MAX_ALLOCATION_BYTES if drive == 'D:' else 0)],
                            capture_output=True, text=True, timeout=20,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        receipt = json.loads(result.stdout.strip())
    except (ValueError, TypeError):
        raise UserError('The AERO storage reserve guard did not return a valid receipt') from None
    if result.returncode or receipt.get('allowed') is not True:
        raise UserError('The AERO storage reserve guard refused the allocation')


def export_bundle(destination, districts):
    """Write a fresh proposal directory. Existing directories are refused."""
    destination = Path(destination).absolute()
    if destination.exists():
        raise UserError('Use a fresh integration bundle directory')
    for parent in destination.parents:
        if parent.is_symlink() or parent.is_junction():
            raise UserError('Linked integration destinations are refused')
    files = bundle_files(copy.deepcopy(districts))
    reserve_allocation(destination)
    destination.mkdir(parents=False)
    for relative, data in files.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, encoding='utf-8', newline='\n')
    return {'files': len(files), 'bytes': sum(len(value.encode('utf-8')) for value in files.values()),
            'status': 'source proposal only; master installs and qualifies the candidate'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from living_world.defaults import configuration
    print(json.dumps(export_bundle(args.output, configuration()['districts'])))


if __name__ == '__main__':
    main()
