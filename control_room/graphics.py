"""Selectable, exact shader pins for explicitly owned local clients."""
from __future__ import annotations

import re
from pathlib import Path

from .common import Layout, REPO, UserError, atomic_write, contained, digest, read_json, utcnow, write_json
from .presentation import closed


def client_layout(layout):
    receipt = read_json(layout.logs / 'playtest-prepared.json', {})
    owner = read_json(layout.state / 'test-owner.json', {})
    if owner.get('owner_source') == str(REPO) and receipt.get('parent'):
        parent = Layout(Path(receipt['parent']))
        if (parent.staging / 'world-tests' / owner.get('id', '')).resolve() == layout.home:
            return parent
    return layout


class Graphics:
    def __init__(self, layout, storage):
        self.layout, self.storage = client_layout(layout), storage

    def client(self, ident):
        if not isinstance(ident, str) or not re.fullmatch(r'AWFT_Check_\d{8}_\d{6}', ident):
            raise UserError('Choose an owned local Prism client')
        instance = contained(self.layout.home, 'instances/' + ident)
        owner = read_json(instance / 'awft-owned.json', {})
        if owner.get('format') != 'awft-owned-client:1' or owner.get('root') != str(instance):
            raise UserError('Client ownership could not be verified')
        return instance, owner

    def snapshot(self):
        data = read_json(REPO / 'catalog/graphics-profiles.json', {'profiles': []})
        shaders = read_json(REPO / 'catalog/shaders.json', {'shaders': []})['shaders']
        pins = {m['slug']:m for m in read_json(REPO / 'catalog/lock.json')['mods'] if m['kind']=='shader'}
        rows = []
        for row in shaders:
            pin = pins.get(row['id'])
            rows.append(row | {'pinned':bool(pin), 'filename':pin['filename'] if pin else None,
                'version':pin['version'] if pin else row.get('version'),
                'cached':bool(pin and (self.layout.caches/'mods'/pin['filename']).is_file())})
        clients = []
        for path in sorted((self.layout.home/'instances').glob('AWFT_Check_*')):
            try:
                instance, owner = self.client(path.name)
                iris = instance/'.minecraft/config/iris.properties'
                text = iris.read_text() if iris.is_file() and iris.stat().st_size<=65536 else ''
                values = dict(re.findall(r'(?m)^([A-Za-z]+)=(.*)$', text))
                clients.append({'id':path.name,'player':owner.get('player'),'shader':values.get('shaderPack'),
                    'enabled':values.get('enableShaders')=='true','revision':digest(iris) if iris.is_file() else None})
            except (UserError, OSError):
                continue
        return data | {'shaders':rows,'clients':clients,'scope':'Applies to a closed owned local client. Other computers choose their shader in Minecraft.'}

    def apply(self, ident, shader, expected, allow_lod_limited=False):
        with self.layout.mutation:
            instance, _ = self.client(ident)
            closed(instance)
            iris = contained(instance,'.minecraft/config/iris.properties')
            if (digest(iris) if iris.is_file() else None) != expected:
                raise UserError('This client’s shader choice changed; refresh before applying')
            if iris.exists() and iris.stat().st_size>65536:
                raise UserError('Iris settings exceed the local editing limit')
            values = {'enableShaders':'false'}
            pin = None
            if shader != 'off':
                pin = next((m for m in read_json(REPO/'catalog/lock.json')['mods'] if m['kind']=='shader' and m['slug']==shader),None)
                row = next((s for s in read_json(REPO/'catalog/shaders.json')['shaders'] if s['id']==shader),None)
                if not pin or not row:
                    raise UserError('Choose an exact pinned shader')
                if row['dh_status'] != 'programs-present' and allow_lod_limited is not True:
                    raise UserError('This shader lacks verified DH support. Acknowledge the distant-terrain limitation before selecting it.')
                source = contained(self.layout.caches,'mods/'+pin['filename'])
                if not source.is_file() or source.stat().st_size != pin['size'] or any(digest(source,alg)!=value for alg,value in pin['hashes'].items()):
                    raise UserError('The pinned shader must be acquired and hash-verified first')
                self.storage.reserve(pin['size']+131072,instance)
                target = contained(instance,'.minecraft/shaderpacks/'+pin['filename'])
                if target.exists() and digest(target) != digest(source):
                    raise UserError('A different local shader file is preserved; review it before replacement')
                if not target.exists():
                    atomic_write(target,source.read_bytes())
                values.update(enableShaders='true',shaderPack=pin['filename'])
            self.storage.reserve(131072,instance)
            text = iris.read_text() if iris.is_file() else ''
            history = contained(instance,'awft-graphics-history/'+str(__import__('time').time_ns())+'.properties')
            atomic_write(history,text)
            for key,value in values.items():
                pattern=r'(?m)^'+key+r'=[^\r\n]*$'
                if re.search(pattern,text):text=re.sub(pattern,lambda _:key+'='+value,text)
                else:text += ('\n' if text and not text.endswith('\n') else '')+key+'='+value+'\n'
            atomic_write(iris,text)
            receipt={'at':utcnow(),'shader':shader,'filename':pin['filename'] if pin else None,
                'previous':str(history),'revision':digest(iris),'status':'Selected for next client launch; rendering acceptance remains pending'}
            write_json(instance/'awft-graphics.json',receipt)
            return receipt
