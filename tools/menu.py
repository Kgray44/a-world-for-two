"""Author small FancyMenu/Drippy layouts; never transform the supplied background."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from control_room.common import REPO, atomic_write, digest, read_json, write_json


def block(kind, values):
    return kind + ' {\n' + ''.join(f'  {k} = {str(v).lower() if isinstance(v, bool) else v}\n' for k, v in values.items()) + '}\n\n'


def element(identifier, kind, anchor, x, y, width, height, **values):
    return block('vanilla_button' if kind == 'vanilla_button' else 'element', dict(values, element_type=kind, instance_identifier=identifier,
        anchor_point=anchor, x=x, y=y, width=width, height=height, stay_on_screen=True,
        stretch_x=False, stretch_y=False, base_opacity=1.0, appearance_delay='no_delay', fade_in_v2='no_fading', fade_out='no_fading'))


def base(identifier):
    return 'type = fancymenu_layout\n\n' + block('layout-meta', dict(identifier=identifier, is_enabled=True, render_custom_elements_behind_vanilla=False, randommode=False, layout_index=0)) + block('menu_background', dict(background_type='image', image_path='[source:local]/config/fancymenu/assets/awft-background.png', repeat_texture=False, slide=False, parallax=False, instance_identifier='awft-still-background')) + block('customization', dict(action='backgroundoptions', keepaspectratio=True)) + block('scroll_list_customization', dict(show_screen_background_overlay_on_custom_background=False, apply_vanilla_background_blur=False))


def generate():
    folder = REPO / 'packwiz/config/fancymenu'
    assets = folder / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    # Render only original typography and control textures, independently of the artwork.
    canvas = Image.new('RGBA', (1080, 264))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(r'C:\Windows\Fonts\georgiab.ttf', 102)
    subtitle = ImageFont.truetype(r'C:\Windows\Fonts\georgiai.ttf', 32)
    draw.text((8, 19), 'A World for Two', font=font, fill='#1c2c27', stroke_width=3, stroke_fill=(10, 20, 18, 110))
    draw.text((5, 14), 'A World for Two', font=font, fill='#fff0d0')
    draw.line((9, 154, 126, 154), fill='#dcbb7c', width=2)
    draw.text((9, 173), 'Our little corner of an endless world.', font=subtitle, fill='#f1e4ca', stroke_width=1, stroke_fill='#26392c')
    canvas.save(assets / 'awft-title.png', optimize=True)
    for state in ('normal', 'hover', 'primary', 'primary-hover'):
        image = Image.new('RGBA', (784, 112))
        pen = ImageDraw.Draw(image)
        fill = {'normal':(20, 44, 36, 178), 'hover':(40, 71, 52, 230), 'primary':(131, 102, 52, 225), 'primary-hover':(161, 127, 66, 245)}[state]
        pen.rounded_rectangle((1, 1, 782, 110), radius=14, fill=fill, outline=(231, 205, 154, 210), width=3)
        pen.line((18, 106, 765, 106), fill=(9, 25, 19, 130), width=3)
        image.save(assets / ('awft-button-' + state + '.png'), optimize=True)
    layout = base('title_screen')
    # A fixed GUI scale keeps the landscape visible at common laptop resolutions.
    layout += block('customization', dict(action='setscale', scale=2.0))
    layout += element('awft-title', 'image', 'top-left', 22, 20, 240, 58, source='[source:local]/config/fancymenu/assets/awft-title.png')
    layout += element('mc_titlescreen_multiplayer_button', 'vanilla_button', 'bottom-right', -184, -160, 160, 24,
        label='Join Our World', hoverlabel='Join Our World', is_hidden=False, navigatable=True,
        backgroundnormal='[source:local]/config/fancymenu/assets/awft-button-primary.png', backgroundhovered='[source:local]/config/fancymenu/assets/awft-button-primary-hover.png')
    for index, (identifier, label) in enumerate([('mc_titlescreen_singleplayer_button','Singleplayer'),('mc_titlescreen_options_button','Settings'),('forge_titlescreen_mods_button','Mods'),('mc_titlescreen_quit_button','Quit')]):
        layout += element(identifier, 'vanilla_button', 'bottom-right', -184, -129 + index * 27, 160, 22,
            label=label, hoverlabel=label, is_hidden=False, navigatable=True,
            backgroundnormal='[source:local]/config/fancymenu/assets/awft-button-normal.png', backgroundhovered='[source:local]/config/fancymenu/assets/awft-button-hover.png')
    for identifier in ('mc_titlescreen_realms_button','minecraft_logo_widget','minecraft_splash_widget','minecraft_branding_widget','minecraft_realms_notification_icons_widget'):
        layout += element(identifier, 'vanilla_button', 'vanilla', 0, 0, 10, 10, is_hidden=True)
    atomic_write(folder / 'customization/awft_title.txt', layout)
    loading = base('drippy_loading_overlay')
    loading += block('customization', dict(action='setscale', scale=2.0))
    loading += element('awft-loading-title', 'image', 'top-left', 22, 20, 420, 103, source='[source:local]/config/fancymenu/assets/awft-title.png')
    loading += element('awft-real-progress', 'progress_bar', 'bottom-right', -240, -60, 216, 5,
        bar_color='#E6C68C', background_color='#183C32B0', direction='right',
        progress_source='{"placeholder":"game_loading_progress"}', value_mode='percentage', smooth_filling_animation=True)
    for identifier in ('mojang_logo', 'progress_bar'):
        loading += element(identifier, 'vanilla_button', 'vanilla', 0, 0, 10, 10, is_hidden=True)
    atomic_write(folder / 'customization/awft_loading.txt', loading)
    atomic_write(folder / 'customizablemenus.txt', 'type = customizablemenus\n\nnet.minecraft.client.gui.screens.TitleScreen {\n}\n\nde.keksuccino.drippyloadingscreen.customization.DrippyOverlayScreen {\n}\n')
    original = read_json(REPO / 'catalog/menu-artwork.json')
    assert digest(assets / 'awft-background.png') == original['sha256']
    write_json(REPO / 'catalog/menu-layout.json', {'background_sha256':original['sha256'], 'authoring':'Original A World for Two typography and control textures; no artwork transformations.', 'layout':'FancyMenu v3 native format', 'runtime_visual_validation':'pending', 'native_actions':['vanilla multiplayer server list','vanilla singleplayer','vanilla options','vanilla NeoForge mods','vanilla quit']})
    print('Authored FancyMenu title and Drippy layouts; supplied background hash unchanged.')


if __name__ == '__main__':
    generate()
