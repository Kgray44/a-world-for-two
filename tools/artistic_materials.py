"""The owner's material rule, including the intentional one-axis exception.

Run per authored building (or complete vessel), including its floors and roofs.
This is a geometry constraint, not an artistic-quality score. Designed dividers,
openings and changes of construction must supply the breaks; this function never
recolors a build or introduces random texture noise.
"""
from __future__ import annotations

from collections import defaultdict


VOID = {'minecraft:air', 'minecraft:cave_air', 'minecraft:void_air', 'minecraft:water'}


def material_run_report(blocks):
    """Describe runs >=4, without treating a long edge as an artistic failure.

    ``blocks`` maps integer (x,y,z) to actual block-state strings. Different state
    orientations of the same block ID count as the same material. This applies
    the owner's rule conservatively across the whole individual building. The
    owner permits unlimited repetition in one axis where it suits the design:
    roof edges, fences, beams and walkway borders are examples. This report
    retains those lengths for visual review instead of forcing arbitrary seams.
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
            for material, axes in sorted(runs.items())]


def material_runs(blocks):
    """Building violations: the same material exceeds three on multiple axes.

    A single long axis is explicitly allowed. Different facing states still
    cannot disguise an unbroken material panel.
    """
    return [row for row in material_run_report(blocks)
            if row['exceeds_three_in_multiple_axes']]


def outdoor_material_runs(blocks):
    """Outdoor fields exceeding nine on multiple axes; long borders are allowed.

    The building three-block rule is not newly imposed on paths or gardens.
    """
    return [row for row in material_run_report(blocks)
            if sum(run['length'] > 9 for run in row['long_runs'].values()) > 1]


def require_material_rule(blocks, name):
    violations = material_runs(blocks)
    if violations:
        raise ValueError(f'{name}: material run rule failed: {violations[:8]}')
    return {'building': name,
            'rule': 'At most one axis exceeds three per block material; intentional one-axis runs have no length cap',
            'state_facing_is_not_a_material_break': True, 'violations': [],
            'one_axis_runs_for_visual_review': material_run_report(blocks),
            'artistic_quality': 'Requires native visual inspection; this geometry check does not certify quality'}


def require_outdoor_rule(blocks, name):
    """Retain breakup of broad outdoor fields while allowing continuous edges."""
    violations = outdoor_material_runs(blocks)
    if violations:
        raise ValueError(f'{name}: outdoor multi-axis material run rule failed: {violations[:8]}')
    return {'area': name,
            'rule': 'No authored same-material field exceeds nine on multiple axes; intentional one-axis borders have no length cap',
            'untouched_natural_terrain': 'not authored geometry', 'violations': [],
            'long_runs_for_visual_review': material_run_report(blocks)}
