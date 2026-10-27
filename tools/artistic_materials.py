"""The owner's three-block material rule, independent of block facing states.

Run per authored building (or complete vessel), including its floors and roofs.
This is a geometry constraint, not an artistic-quality score. Designed dividers,
openings and changes of construction must supply the breaks; this function never
recolors a build or introduces random texture noise.
"""
from __future__ import annotations

from collections import defaultdict


VOID = {'minecraft:air', 'minecraft:cave_air', 'minecraft:void_air', 'minecraft:water'}


def material_runs(blocks):
    """Flag a run >=10 anywhere, or runs >=4 in two or more axes.

    ``blocks`` maps integer (x,y,z) to actual block-state strings. Different state
    orientations of the same block ID count as the same material. This applies
    the owner's rule conservatively across the whole individual building.
    """
    cells = {tuple(p): state.split('[', 1)[0] for p, state in blocks.items()
             if state.split('[', 1)[0] not in VOID}
    runs = defaultdict(dict)
    for position, material in cells.items():
        for axis, name in enumerate(('x', 'y', 'z')):
            previous = list(position)
            previous[axis] -= 1
            if cells.get(tuple(previous)) == material:
                continue
            cursor = list(position)
            length = 1
            while True:
                cursor[axis] += 1
                if cells.get(tuple(cursor)) != material:
                    break
                length += 1
            if length >= 4 and length > runs[material].get(name, {}).get('length', 0):
                runs[material][name] = {'length': length, 'from': list(position), 'to': cursor[:axis]+[cursor[axis]-1]+cursor[axis+1:]}
    return [{'material': material, 'long_runs': axes,
             'exceeds_nine': any(row['length'] > 9 for row in axes.values()),
             'exceeds_three_in_multiple_axes': len(axes) > 1}
            for material, axes in sorted(runs.items())
            if len(axes) > 1 or any(row['length'] > 9 for row in axes.values())]


def require_material_rule(blocks, name):
    violations = material_runs(blocks)
    if violations:
        raise ValueError(f'{name}: material run rule failed: {violations[:8]}')
    return {'building': name, 'rule': 'No run exceeds nine; at most one axis exceeds three per block material',
            'state_facing_is_not_a_material_break': True, 'violations': []}


def require_outdoor_rule(blocks, name):
    """The nine-block cap also covers authored streets, gardens and foundations."""
    violations = [row for row in material_runs(blocks) if row['exceeds_nine']]
    if violations:
        raise ValueError(f'{name}: outdoor nine-block run rule failed: {violations[:8]}')
    return {'area': name, 'rule': 'No authored same-material run exceeds nine in any axis',
            'untouched_natural_terrain': 'not authored geometry', 'violations': []}
