"""Additive service/deck furnishing recipes; no world selection or runtime calls.

Call decorate() on a completed, rope-finished FleetShip before serializing it.
Every target must have been explicit AIR at entry, including weather-deck props;
missing coordinates never count as surveyed or authored air. New casks/cabinets
are empty. Existing furniture, tags, stock, guns and mechanics remain untouched.
"""
from __future__ import annotations

import json

from control_room.common import UserError
from tools.grand_harbor_fleet import AIR, SPECS, circulation, identifier
from tools.artistic_ship import SEAL_BLOCKS


def decorate(p):
    """Return named local-coordinate detail groups, or refuse without a delta."""
    if p.spec.key not in SPECS:
        raise UserError('Deck furnishings require one of the three new major ships')
    before, old_tags = dict(p.blocks), dict(p.tags)
    old_required = set(p.required_ids)
    circulation(p)
    s, groups = p.spec, []
    gun, mess, weather = s.decks[2], s.decks[1], s.weather
    reserved = set(p.route_clearance) | set(p.hatch_clearance)
    # Preserve the established continuous service lane, not merely room reachability.
    for floor in s.decks[:4]:
        reserved.update((x, floor+dy, z) for x in (2, 3) for dy in (1, 2)
                        for z in range(s.fore, s.aft+1))
    for room in p.rooms:
        x, y, z = room['local_anchor']
        reserved.update(((x, y+1, z), (x, y+2, z)))
    for (x, y, z), state in before.items():
        if '_stairs[' in state and 'half=bottom' in state:
            reserved.update(((x, y+1, z), (x, y+2, z)))
    for x, y, z in p.emergency_ladder:
        reserved.update(((x-1, y, z), (x-1, y+1, z)))
    for fitting in p.fittings:
        if fitting['kind'] == 'stopped cargo derrick':
            x1, y1, z1, x2, y2, z2 = fitting['load_sweep_bounds']
            reserved.update((x, y, z) for x in range(x1, x2+1)
                            for y in range(y1, y2+1) for z in range(z1, z2+1))
    for gun_position in p.guns:
        x, y, z = gun_position['breech']
        inward = 1 if x < 0 else -1
        reserved.update((x+inward*n, yy, zz) for n in (1, 2)
                        for yy in (y-1, y) for zz in (z-1, z, z+1))
    # Full two-wide sea-stair approach remains clear across the weather deck.
    reserved.update((x, weather+dy, z) for x in range(3, p.width(0, weather)+weather+3)
                    for dy in (1, 2) for z in (0, 1))

    def prop(key, **properties):
        return key, properties

    plate = prop('handcrafted:blue_plate', facing='east', pieces=3, waterlogged=False)
    cups = prop('handcrafted:blue_cup', facing='east', pieces=2, waterlogged=False)
    ledger = prop('handcrafted:stackable_book', facing='east', books=2, seed=3)
    basin = prop('handcrafted:terracotta_wide_pot')
    crock = prop('handcrafted:terracotta_thick_pot')
    linen = prop('chipped:bundled_white_wool')
    board = prop('farmersdelight:cutting_board', facing='east', waterlogged=False)

    def group(name, rows, purpose):
        groups.append({'name': name, 'rows': rows, 'purpose': purpose})

    def counter(name, x, zs, tops, *, cabinet=False, purpose):
        lower = (prop('farmersdelight:spruce_cabinet', facing='east' if x < 0 else 'west', open=False)
                 if cabinet else prop('handcrafted:dark_oak_table', color='none', shape='single', waterlogged=False))
        rows = []
        for z, top in zip(zs, tops, strict=True):
            rows.extend(((x, gun+1, z, *lower), (x, gun+2, z, *top)))
        group(name, rows, purpose)

    def deck_group(name, cells, purpose):
        rows = []
        for x, z, kind in cells:
            choices = {
                'cask': prop('minecraft:barrel', facing='up', open=False),
                'case': prop('chipped:spruce_crate', facing='up', open=False),
                'linen': linen,
                'canvas': prop('chipped:patched_white_wool'),
                'grain': prop('minecraft:hay_block', axis='y'),
                'signal': prop('minecraft:red_wool'),
                'bench': prop('handcrafted:dark_oak_bench', facing='east' if x < 0 else 'west',
                              color='none', shape='single', waterlogged=False),
            }
            rows.append((x, weather+1, z, *choices[kind]))
        group(name, rows, purpose)

    if s.key == 'golden-petrel':
        counter("Victualler's issuing dresser", 5, range(-25, -21), (crock, board, plate, cups),
                cabinet=True, purpose='Opposite the original cold galley: crockery, bread board and serving ware')
        counter('Grain factor tally and inspection bench', 7, range(-7, -3), (ledger, basin, board, crock),
                purpose='Merchant accounts and a dry grain-sampling bowl, clear of the gun battery')
        counter('Gunner swab-water and cloth bench', -6, range(-12, -9), (basin, linen, board),
                purpose='Inert maintenance station; no shot, charge, ammunition or firing changes')
        group('Victualling reserve casks', [(8, gun+1, z, 'minecraft:barrel', {'facing':'up','open':False})
              for z in (3, 4, 5)], 'A small accessible issue reserve; all three new casks are empty')
        deck_group('Incoming merchant casks and tally cases',
                   [(x,z,'case' if (x+z)%3 == 0 else 'cask') for x in (6,7) for z in (-21,-20,-19,-18)]
                   + [(8,-19,'case')],
                   'A compact receiving group forward of the port derrick and clear of the boarding lane')
        deck_group('Folded working sailcloth and cooper cases',
                   [(-6,-21,'canvas'),(-7,-21,'case'),(-6,-20,'linen'),(-7,-20,'case'),
                    (-6,-19,'canvas'),(-7,-19,'cask')], 'Bounded low canvas stores beside the rail')
        deck_group('Market grain and outward cases',
                   [(7,6,'grain'),(8,6,'case'),(9,6,'case'),(7,7,'cask'),(8,7,'grain'),
                    (9,7,'case'),(7,8,'case'),(8,8,'cask')], 'Grain forms and sealed cases tell the victualling role')
        deck_group('Merchant watch rest and working casks',
                   [(-6,12,'bench'),(-6,13,'bench'),(-6,14,'bench'),(-7,12,'cask'),(-7,14,'case')],
                   'A rail-side rest outside the ship boat and the central stair trunk')
        # The original companionway has removed the station11 table. Start at12
        # rather than furnishing the air over that real open stair/service area.
        mess_name, mess_tops = 'Victualler crew table laid for supper', (plate, cups, crock, ledger)
    elif s.key == 'resolute-wren':
        counter('Dispatch watch hot-drink dresser', -4, range(-23, -20), (cups, crock, board),
                cabinet=True, purpose='A compact port-side issue counter opposite the existing starboard galley')
        counter('Patrol gunner maintenance bench', -5, range(-15, -11), (basin, board, linen, crock),
                purpose='Tools and cleaning cloth between gun stations, leaving the breech approaches open')
        counter('Courier sorting and watch ledger', 4, range(-3, 0), (ledger, cups, ledger),
                purpose='Two visible book groups and a watch drink beside the retained starboard passage')
        counter('Returning watch wash and issue table', 5, (10,11), (basin, plate),
                purpose='Small patrol-watch service station, separated from the gun at station13')
        deck_group('Sealed dispatch cases and recognition canvas',
                   [(4,-18,'case'),(5,-18,'case'),(4,-17,'signal'),(5,-17,'case'),(4,-16,'cask'),(5,-16,'case')],
                   'A restrained red recognition cloth among sealed courier cases')
        deck_group('Patrol boat-party line and repair stores',
                   [(-4,-18,'case'),(-5,-18,'canvas'),(-4,-17,'case'),(-5,-17,'cask')],
                   'A distinct small work group that preserves the adjacent derrick ladder')
        deck_group('Storm canvas and spare fender bundles',
                   [(-7,-6,'canvas'),(-6,-6,'case'),(-7,-5,'linen'),(-6,-5,'case'),(-7,-4,'canvas'),(-6,-4,'cask')],
                   'Low folded material outboard of the existing cargo-hatch coaming')
        deck_group('Patrol lookout rest and water cask',
                   [(6,10,'bench'),(6,11,'bench'),(6,12,'bench'),(5,10,'cask'),(5,12,'case')],
                   'A small watch rest before the raised quarterdeck, outside the boat skids')
        mess_name, mess_tops = 'Patrol watch mess with duty book', (cups, plate, ledger, cups, plate)
    else:
        counter('Relief ration issue dresser', 5, range(-32,-28), (crock, board, plate, cups),
                cabinet=True, purpose='Serving ware opposite the galley for the relief vessel provisioning party')
        counter('Surgeon clean preparation dresser', -6, range(-14,-10), (basin, linen, cups, ledger),
                cabinet=True, purpose='Dry wash bowl, folded dressings, cups and case notes; no treatment claim')
        counter('Patient water and washing alcove', 7, range(2,6), (basin, crock, cups, basin),
                purpose='A second wash and drink station, away from the existing surgeon berth below')
        counter('Stretcher and linen repair bench', -7, range(-6,-2), (linen, board, linen, ledger),
                purpose='Folded canvas, repair board and duty record; no entity stretcher or new mechanics')
        deck_group('Relief receiving casks and provision cases',
                   [(x,z,'cask' if (x+z)%3 == 0 else 'case') for x in (6,7,8) for z in (-23,-22,-21)],
                   'A visible receiving group for provisioning rather than a duplicate merchant grain cargo')
        deck_group('Clean linen and covered dressing cases',
                   [(x,z,'linen' if (x+z)%2 else 'case') for x in (-8,-7,-6) for z in (-23,-22,-21)],
                   'White folded material and closed cases identify the relief mission')
        deck_group('Boat-party ration and rest station',
                   [(6,10,'bench'),(6,11,'bench'),(6,12,'bench'),(7,10,'cask'),(8,10,'case'),
                    (7,12,'case'),(8,12,'cask')], 'Low seating and closed cases clear of the boarding stairs')
        deck_group('Relief unloading canvas and spare case group',
                   [(-8,11,'case'),(-7,11,'canvas'),(-6,11,'case'),(-8,12,'cask'),(-7,12,'linen'),
                    (-6,12,'case'),(-8,13,'case'),(-7,13,'canvas')], 'A separate aft unloading group outside the boat cradle')
        mess_name, mess_tops = 'Relief crew mess with washing crock', (plate, cups, basin, plate, cups)

    mess_z = -28 if s.key == 'mercy-of-the-tide' else 12 if s.key == 'golden-petrel' else 11
    group(mess_name, [(-4, mess+2, mess_z+i, *top) for i,top in enumerate(mess_tops)],
          'Tabletop additions use only retained original mess tables; their bases and seating are unchanged')

    rows = [row for group_data in groups for row in group_data['rows']]
    if len(rows) > 160:
        raise UserError('Keep the deck enrichment below its finite160-cell recipe bound')
    planned, owner, conflicts = {}, {}, []
    for group_data in groups:
        for x,y,z,key,properties in group_data['rows']:
            pos = x,y,z
            if pos in planned:
                raise UserError('Two deck detail groups overlap at '+str(pos))
            if before.get(pos) != AIR or pos in old_tags or pos in reserved:
                conflicts.append((pos, group_data['name']))
                continue
            planned[pos] = p.state(key, **properties)
            owner[pos] = group_data['name']
    if conflicts:
        raise UserError('Deck detail requires unreserved explicit baseline AIR: '+str(conflicts[:16]))
    supports = set(SEAL_BLOCKS) | {'minecraft:stone_bricks', 'minecraft:barrel',
        'handcrafted:dark_oak_table', 'farmersdelight:spruce_cabinet'}
    for x,y,z in planned:
        below = (x,y-1,z)
        if identifier(planned.get(below, before.get(below, ''))) not in supports:
            raise UserError('Deck prop lacks a full floor or intended tabletop: '+str((x,y,z)))
    # This is an in-memory atomic source operation, never a world rollback/replay.
    try:
        for x,y,z,key,properties in rows:
            p.put(x,y,z,key,**properties)
            if key in {'minecraft:barrel','farmersdelight:spruce_cabinet'}:
                title = owner[x,y,z]+' — empty'
                p.tag(x,y,z,'{CustomName:'+json.dumps(json.dumps({'text':title}))+',Items:[]}')
        circulation(p)
    except Exception:
        p.blocks.clear(); p.blocks.update(before)
        p.tags.clear(); p.tags.update(old_tags)
        p.required_ids.clear(); p.required_ids.update(old_required)
        raise
    return [{'name': row['name'], 'local_cells': [[x,y,z] for x,y,z,*_ in row['rows']],
             'purpose': row['purpose']} for row in groups]
