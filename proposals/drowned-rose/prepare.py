"""Build isolated source assets and proposed manifests, without installing anything."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
import sys
import uuid

from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(HERE))
from control_room.pack import generate_pack

NAMES=[
 ('mara-reef','Mara Reef','vielle player','patient storyteller'),
 ('kit-cordage','Kit Cordage','lute player','cheerful improviser'),
 ('ivo-gull','Ivo Gull','flute player','quiet observer'),
 ('nels-tap','Nels Tap','drummer','boisterous optimist'),
 ('ada-brine','Ada Brine','sailmaker','practical and sociable'),
 ('oona-kelp','Oona Kelp','navigator','curious and reflective'),
 ('tamsin-cask','Tamsin Cask','merchant','wry negotiator'),
 ('roan-pike','Roan Pike','retired privateer','reserved and loyal'),
 ('bea-copper','Bea Copper','shipwright','inventive and patient'),
 ('finn-rusk','Finn Rusk','cook','warm and teasing'),
 ('jory-salt','Jory Salt','deckhand','restless and friendly'),
 ('esme-lantern','Esme Lantern','lamplighter','gentle observer'),
 ('sable-vane','Sable Vane','cartographer','precise and inquisitive'),
 ('pax-barley','Pax Barley','brewer','expansive storyteller'),
 ('rhea-hook','Rhea Hook','fisher','laconic and kind'),
 ('orin-pearl','Orin Pearl','diver','adventurous and sociable'),
 ('lina-splice','Lina Splice','rope maker','thoughtful and humorous'),
 ('cass-flint','Cass Flint','powder merchant','careful and skeptical'),
 ('dara-moss','Dara Moss','herbalist','calm and curious'),
 ('toby-keel','Toby Keel','carpenter','jovial and practical'),
 ('vera-coil','Vera Coil','lookout','watchful and witty'),
 ('sol-drift','Sol Drift','traveler','dreamy storyteller'),
 ('nell-tide','Nell Tide','dock clerk','organized and friendly'),
 ('arlo-ink','Arlo Ink','scribe','dry wit and curiosity'),
 ('miri-coin','Miri Coin','trader','confident and generous'),
 ('duke-nettle','Duke Nettle','sailor','gruff with a soft heart'),
 ('hester-wake','Hester Wake','boat pilot','steady and sociable'),
 ('pip-shoal','Pip Shoal','courier','energetic and curious'),
 ('yara-cedar','Yara Cedar','civilian potter','reflective and warm'),
 ('silas-rose','Silas Rose','harbor fiddler','playful and absentminded'),
 ('val-kestrel','Val Kestrel','weather reader','restless observer'),
 ('penny-marl','Penny Marl','clay pipe maker','warm skeptic'),
 ('oskar-bell','Oskar Bell','ship bell founder','patient perfectionist'),
 ('niamh-wick','Niamh Wick','candle merchant','shrewd and theatrical'),
 ('bert-oar','Bert Oar','ferryman','dry and practical'),
 ('suri-clove','Suri Clove','spice trader','curious and generous'),
 ('moss-rigging','Moss Rigging','rigger','quiet and observant'),
 ('hedda-stern','Hedda Stern','retired bosun','brisk but fair'),
 ('rowe-amber','Rowe Amber','beachcomber','whimsical collector'),
 ('pella-thorn','Pella Thorn','surgeon','precise and unflappable'),
 ('gus-brass','Gus Brass','tinker','inventive and distracted'),
 ('anya-skiff','Anya Skiff','small boat builder','confident and amused'),
 ('corin-stave','Corin Stave','wine factor','fussy and companionable'),
 ('vesper-rill','Vesper Rill','itinerant singer','wistful and playful'),
 ('edda-quill','Edda Quill','notary','quiet with a sharp wit'),
]
LINES=[
 "My bow has survived three storms. The audience has survived four rehearsals.",
 "I tuned this lute to the tide. Apparently the tide is a little sharp.",
 "The gulls keep requesting solos. Their timing is terrible.",
 "A quiet drum? Certainly. I charge extra for the missing thunder.",
 "That sail will hold. I used the thread reserved for stubborn captains.",
 "North is easy. Finding a captain willing to go there is the trick.",
 "I sell honest measures. The stories are generously oversized.",
 "I retired from piracy. Keeping the hat seemed reasonable.",
 "A ship is just a large cupboard with rather dramatic leaks.",
 "The stew contains no treasure. People kept chipping their spoons.",
 "I swabbed the deck twice. The sea remains unimpressed.",
 "The lamps are lit. Now the shadows must pay for their own drinks.",
 "I left space on the map for places the captain insists exist.",
 "The barrel is breathing. That means it is working harder than me.",
 "The fish was this big. The bill for losing the net was bigger.",
 "The pearl was real. My tale of the sea monster has editorial flourishes.",
 "Every knot has a purpose. Some are simply arguments with rope.",
 "Please keep the candle away from my sample case. And my eyebrows.",
 "This tea cures impatience. It takes a surprisingly long time to brew.",
 "The table does not wobble. The floor is expressing an opinion.",
 "I can see the harbor from here. Mostly I am watching my unattended chips.",
 "I followed a star here. The smell of supper handled the last turn.",
 "Three arrivals, two departures, and one captain who forgot his own ship.",
 "I wrote down every word. The spelling of 'aargh' is still under review.",
 "I made a fair trade: my spare compass for a story worth getting lost in.",
 "I am not sentimental. I simply remember every dog in every port.",
 "A safe landing is mostly patience, with a little shouting at the wind.",
 "Your letter arrived dry. My boots would like that arrangement next time.",
 "I made the mugs with broad handles. Sailors tell stories with both hands.",
 "I came for one song and stayed for the chorus. That was last Thursday.",
 "Those clouds promise rain. I have asked them to put it in writing.",
 "A clay pipe needs patience. Its owner usually needs considerably more.",
 "I cast bells for ships. Captains ask for a tone that sounds expensive.",
 "My candles last all evening, provided nobody spends the evening measuring them.",
 "The ferry runs both ways. That surprises a remarkable number of passengers.",
 "One clove in the stew, two in a captain's pocket. Follow the fragrant one.",
 "I trust a rope after inspecting it. People take a little longer.",
 "A tidy deck is a kind deck. Bare feet remember every loose nail.",
 "The tide left me a blue bottle. I am waiting for the sea to explain itself.",
 "Hold still. I have removed splinters from far less cooperative furniture.",
 "This pocket watch now tells the tide. The hours were getting repetitive.",
 "A little boat tells you its troubles before a big ship admits to having any.",
 "Let the wine breathe. The captain has been doing all the talking.",
 "I know a song for every departure. Arrivals require a second drink.",
 "Sign here. Your dramatic flourish may extend into the margin, not the terms.",
]


def roster():
    from dialogue_profiles import EXTRA_LINES
    rows=[]
    acts=['sit','social','walk','bar','watch','window','group','return','drink']
    for i,((ident,name,role,personality),line) in enumerate(zip(NAMES,LINES)):
        preferences={a:2+((i*7+j*3)%7) for j,a in enumerate(acts)}
        preferences['watch']=8 if i<4 else preferences['watch']
        rows.append({'id':ident,'name':name,'role':role,'personality':personality,
                     'uuid':str(uuid.UUID(bytes=hashlib.md5(('awft:drowned-rose:'+ident).encode(),usedforsecurity=False).digest(),version=3)),
                     'preferred_instrument':['vielle','lute','flute','tiny_drum'][i%4],
                     'preferences':preferences,
                     'social_preferences':[NAMES[(i+1)%(30 if i<30 else len(NAMES))][0],NAMES[(i+7)%(30 if i<30 else len(NAMES))][0]],
                     'residency':'The Drowned Rose, Tortuga',
                     'appearance':f'Original local skin {i+1}; varied skin, hair, shirt, sash and trousers',
                     'dialogue':[line,*EXTRA_LINES[ident]]})
    return rows


def skin(index,path):
    """Original procedural skin atlas, never remote player skins or copied art."""
    skins=[(204,150,112),(110,70,48),(236,189,150),(154,99,66),(188,127,88)]
    shirts=[(38,91,92),(135,49,53),(63,71,107),(119,83,45),(66,99,64),(121,81,111)]
    skin=skins[index%5];shirt=shirts[index%6];hair=[(48,30,24),(102,64,34),(168,113,54),(190,181,165)][index%4]
    image=Image.new('RGBA',(64,64),(0,0,0,0));d=ImageDraw.Draw(image)
    # Cuboid atlas regions: all faces have opaque base colour, overlays stay clear.
    for box,color in [((0,0,31,15),skin),((16,16,39,31),shirt),((40,16,55,31),shirt),
                      ((0,16,15,31),(48+index%4*8,45,41)),((16,48,31,63),(48+index%4*8,45,41)),
                      ((32,48,47,63),shirt)]:d.rectangle(box,fill=(*color,255))
    d.rectangle((0,0,31,7),fill=(*hair,255));d.rectangle((8,8,15,9),fill=(*hair,255))
    d.rectangle((10,11,10,11),fill=(30,30,24,255));d.rectangle((13,11,13,11),fill=(30,30,24,255))
    d.rectangle((11,14,12,14),fill=(111,56,45,255))
    for x,y in [(20,20),(44,20),(36,52)]:
        d.line((x,y+6,x+7,y+6),fill=(214,174,83,255),width=2)
    d.rectangle((44,28,47,31),fill=(*skin,255));d.rectangle((36,60,39,63),fill=(*skin,255))
    if index%3==0:d.rectangle((8,9,15,9),fill=(32,28,28,255))
    if index%4==0:d.rectangle((8,13,15,15),fill=(*hair,255))
    image.save(path)


def prepare(output,dependencies,include_config_ui=False):
    if output.exists():raise ValueError('Fresh owned output directory required')
    output.mkdir(parents=True)
    resources=output/'resources';textures=resources/'assets/awft_tavern/textures/entity';textures.mkdir(parents=True)
    (resources/'roster.json').write_text(json.dumps(roster(),indent=2)+'\n',encoding='utf8')
    for i,row in enumerate(roster()):skin(i,textures/(row['id']+'.png'))
    lock=json.loads((ROOT/'catalog/lock.json').read_bytes())
    lock['version']='0.1.0-drowned-rose-proposal';lock['release_status']='uninstalled proposal; not game qualified'
    modules=['easy-npc-core']+(['easy-npc-config-ui']if include_config_ui else[])
    for slug in modules:
        version=json.loads((dependencies/(slug+'-version.json')).read_bytes());f=next(f for f in version['files']if f['primary'])
        assert not any(m['project_id']==version['project_id']for m in lock['mods'])
        lock['mods'].append({'slug':slug,'name':slug.replace('-',' ').title(),'project_id':version['project_id'],
                            'version_id':version['id'],'version_number':version['version_number'],
                            'filename':f['filename'],'url':f['url'],'hashes':f['hashes'],'size':f['size'],
                            'side':'both','kind':'mod','request':slug,'dependencies':version['dependencies'],
                            'source':'https://modrinth.com/mod/'+slug})
    (output/'proposed-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
    payload=[]
    for name in ['config','defaultconfigs','options.txt']:
        source=ROOT/'packwiz'/name
        payload.extend(p for p in (source.rglob('*')if source.is_dir()else[source])if p.is_file())
    if sum(p.stat().st_size for p in payload)>8*1024**2:raise ValueError('Baseline payload exceeds8MiB; revise storage allocation')
    for path in payload:
        target=output/'packwiz'/path.relative_to(ROOT/'packwiz');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    generate_pack(output/'packwiz',lock)
    (output/'source-roster.json').write_text(json.dumps(roster(),indent=2)+'\n')
    print(json.dumps({'output':str(output),'roster':len(NAMES),'original_skin_assets':len(NAMES),'pack':'isolated dependency proposal; adapter requires separate reviewed artifact pin','modules':modules,'installed':False}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--dependencies',type=Path,required=True);p.add_argument('--include-config-ui',action='store_true');a=p.parse_args();prepare(a.output,a.dependencies,a.include_config_ui)
