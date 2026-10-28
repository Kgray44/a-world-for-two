"""Request actual, authenticated Minecraft framebuffer views from the QA helper."""
from __future__ import annotations

import argparse
import json
import math
import shutil
import time
from pathlib import Path

from control_room.common import UserError, read_json, write_json, digest, utcnow


CLIENT = Path(r'D:\A World for Two\instances\AWFT_Check_20261026_214756\.minecraft')
VIEWS = [
    ('spawn-plaza', [1120.5,67,-1129.5], [1140,71,-1108]),
    ('high-street', [1127.5,67,-1085.5], [1150,73,-1060]),
    ('market', [1080.5,67,-1149.5], [1094,71,-1157]),
    ('residential', [1082.5,67,-1090.5], [1097,72,-1075]),
    ('cottage', [1077.5,67,-1064.5], [1088,73,-1055]),
    ('waterfront', [1095.5,65,-1226.5], [1093,73,-1214]),
    ('tavern', [1089.5,65,-1208.5], [1097,71,-1209]),
    ('alley', [1092.5,65,-1199.5], [1094,69,-1191]),
    ('shipyard', [1150.5,65,-1242.5], [1140,75,-1320]),
    ('bridge-water', [1171.5,64,-1144.5], [1193,73,-1144]),
    ('bridge-road', [1192.5,71,-1180.5], [1193,74,-1143]),
    ('bridge-panorama', [1155,100,-1144], [1193,72,-1144]),
    ('castle-approach', [1210.5,67,-925.5], [1210,84,-975]),
    ('castle-court', [1210.5,67,-972.5], [1210,82,-1008]),
    ('town-panorama', [1110,122,-1214], [1165,74,-1093]),
    ('ship-bow', [1158,65,-1389], [1140,81,-1434]),
    ('ship-stern', [1160,65,-1505], [1140,76,-1488]),
    ('ship-broadside', [1192,65,-1450], [1140,85,-1450]),
    ('ship-quarter', [1177,109,-1498], [1140,82,-1450]),
]


def wait_for(path, timeout=40):
    deadline = time.monotonic()+timeout
    while time.monotonic()<deadline:
        if path.is_file():
            return
        time.sleep(.5)
    raise UserError('The actual client did not complete the request; no substitute image is produced: '+str(path))


def capture(stage_home, name, position, target, *, prefix, settle=8):
    qa = CLIENT/'awft-qa'
    owner = read_json(Path(stage_home)/'dashboard/artistic-owner.json', {})
    auth = read_json(qa/'authorization.json', {})
    if owner.get('format')!='awft-artistic-stage:1' or auth.get('server')!='127.0.0.1:25575':
        raise UserError('Artistic stage and explicit loopback authorization required')
    ident = prefix+'-'+name
    if len(ident)>58 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in ident):
        raise UserError('Choose a short unique view identifier')
    pose = ident+'-pose'
    image = CLIENT/'screenshots'/('awft-qa-'+ident+'.png')
    if image.exists() or (qa/(pose+'.json')).exists() or (qa/(ident+'.json')).exists():
        raise UserError('Every framebuffer capture must have a new immutable identifier')
    dx,dz=target[0]-position[0],target[2]-position[2]
    dy=target[1]-(position[1]+1.62)
    yaw=math.degrees(math.atan2(-dx,dz))
    pitch=-math.degrees(math.atan2(dy,math.hypot(dx,dz)))
    write_json(qa/'request.json', {'nonce':auth['nonce'],'id':pose,'action':'pose',
        'position':position,'yaw':yaw,'pitch':pitch,'gamemode':'spectator'})
    wait_for(qa/(pose+'.json'))
    time.sleep(settle)
    write_json(qa/'request.json', {'nonce':auth['nonce'],'id':ident,'action':'capture',
        'expected_position':position,'expected_look_at':target})
    wait_for(qa/(ident+'.json'))
    wait_for(image)
    native=read_json(qa/(ident+'.json'))
    if native.get('server')!='127.0.0.1:25575' or sum((a-b)**2 for a,b in zip(native['position'],position))>9:
        raise UserError('Actual capture position/server differs; image retained privately')
    output=Path(stage_home)/'logs/visual-review'/prefix
    output.mkdir(parents=True,exist_ok=True)
    destination=output/(name+'.png')
    if destination.exists():raise UserError('Never overwrite a prior visual review')
    shutil.copy2(image,destination)
    receipt={'at':utcnow(),'image':destination.name,'sha256':digest(destination),
        'bytes':destination.stat().st_size,'name':name,'stage':owner['id'],
        'source_pack_sha256':owner['pack_sha256'],'native':native,
        'requested_view':{'feet':position,'look_at':target,'yaw':yaw,'pitch':pitch},
        'evidence':'Actual Minecraft framebuffer with release-excluded QA capture helper; no substitute rendering',
        'artistic_acceptance':'Pending visual inspection; capture alone does not establish quality'}
    write_json(output/(name+'.json'),receipt)
    print(json.dumps({'image':str(destination),'sha256':receipt['sha256'],'fps':native.get('fps')}),flush=True)
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--home',required=True,type=Path)
    parser.add_argument('--prefix',required=True)
    parser.add_argument('--views',nargs='*')
    args=parser.parse_args()
    for name,position,target in VIEWS:
        if args.views and name not in args.views:continue
        capture(args.home,name,position,target,prefix=args.prefix)
