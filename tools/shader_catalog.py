"""Inspect exact author shader archives and generate the Control Room catalog."""
import zipfile
from pathlib import Path
from control_room.common import REPO, read_json, write_json, utcnow

STYLES = {
    'bsl-shaders': ('Warm and cozy', 'Balanced to high', 'Soft light and a familiar cinematic look.'),
    'complementary-reimagined': ('Warm and cozy', 'Balanced to high', 'Minecraft-styled clouds and warm interiors.'),
    'complementary-unbound': ('Cinematic', 'High', 'Realistic water, skies and dramatic lighting; used in the owner playtest.'),
    'kappa-shader': ('Realistic', 'High', 'Detailed clouds, volumetric fog and screen-space path tracing. This exact 5.3 ZIP has no DH terrain programs; distant-terrain compatibility is limited.'),
    'bliss-shader': ('Warm fantasy', 'Balanced to high', 'Changing skies, warm light and varied fantasy atmosphere.'),
    'photon-shader': ('Natural', 'Balanced to high', 'Gameplay-focused, semi-realistic light with scalable clouds and effects. Version 1.4 adds Colorwheel integration; our Create combination still needs testing.'),
    'makeup-ultra-fast-shaders': ('Flexible and cozy', 'Lighter to balanced', 'Optional effects and several color schemes; start with Medium and tune after measurement.'),
    'solas-shader': ('Cozy fantasy', 'Balanced to high', 'Auroras, fireflies, colored lighting and expressive fantasy skies.'),
}


def build():
    review = read_json(REPO / 'catalog/build-inputs/shader-resolved.json')
    lock = read_json(REPO / 'catalog/lock.json')
    items = {m['slug']:m for m in lock['mods'] if m['kind'] == 'shader'}
    items.update({m['slug']:m for m in review['mods']})
    rows = []
    for slug, item in items.items():
        path = Path(r'D:\A World for Two\caches\mods') / item['filename']
        with zipfile.ZipFile(path) as archive:
            programs = [n for n in archive.namelist() if n.endswith(('dh_terrain.vsh', 'dh_terrain.fsh', 'dh_water.vsh', 'dh_water.fsh'))]
        style, cost, description = STYLES.get(slug, ('Cinematic', 'Balanced to high', item['selection_reason']))
        rows.append({'id':slug, 'name':item['name'], 'style':style, 'cost':cost, 'description':description,
            'source':item['source'], 'dh_status':'programs-present' if programs else 'unverified-or-absent',
            'dh_note':'DH shader programs are present; exact Iris/DH/modpack runtime testing is pending.' if programs else 'No DH terrain/water programs found in this exact author ZIP. Iris rendering acceptance is pending.',
            'validation':'Pinned author release inspected; no measured FPS or complete rendering acceptance.'})
    rows.append({'id':'chocapic13-shaders', 'name':'Chocapic13 Shaders (original)', 'version':'V9 / V9.1 beta under investigation',
        'style':'Classic warm light', 'cost':'Preset dependent',
        'description':'The original author download is required. It is not replaced by Bliss. Legacy release, Iris/DH support unverified.',
        'source':'https://www.curseforge.com/minecraft/shaders/chocapic13-shaders', 'dh_status':'unverified-or-absent',
        'dh_note':'No compatibility claim. Official automated download returned HTTP 403; unchanged original file needed.',
        'validation':'Pending author download and native client test.'})
    write_json(REPO / 'catalog/shaders.json', {'at':utcnow(),
        'quality_cost_boundary':'Style and intended cost are author descriptions and configuration guidance, not benchmarks. Download counts indicate popularity rather than a measured quality ranking.', 'shaders':rows})
    write_json(REPO / 'evidence/research/chocapic13-shaders.json', {
        'source':'https://www.curseforge.com/minecraft/shaders/chocapic13-shaders/files/3059792',
        'observed':'Official automated download returned HTTP 403; an unchanged original author download is required.'})
    write_json(REPO / 'evidence/research/pastel-shaders.json', {'source':'https://modrinth.com/shader/pastel-shaders',
        'observed':'Author 1.200 release w3Pxx3b4; exact Iris and DH tests pending. Not in active candidate.'})
    print('Shader catalog:', len(rows))


if __name__ == '__main__':
    build()
