"""Relative LIFE habitat schematics. No absolute coordinates or native execution."""
from __future__ import annotations

import json

BED = "adorablehamsterpets:hamster_bed[occupied=false,orientation=north,upside_down=false,wood_variant=oak]"
LEAVES = "minecraft:oak_leaves[distance=7,persistent=true,waterlogged=false]"


def build_habitats():
    habitats = []
    for key, width, depth, height, entity in (
        ("homestead-hamsters", 11, 9, 6, "adorablehamsterpets:hamster"),
        ("south-shore-gliders", 15, 15, 13, "animalgarden_sugarglider:sugarglider"),
    ):
        blocks = {}

        def put(x, y, z, state):
            blocks[x, y, z] = state

        def fill(x0, x1, y0, y1, z0, z1, state):
            for x in range(x0, x1 + 1):
                for y in range(y0, y1 + 1):
                    for z in range(z0, z1 + 1):
                        put(x, y, z, state)

        # A framed conservatory/aviary: gliders climb ordinary fences, so a
        # continuous roof and walls are required before admitting residents.
        for x in range(width):
            for z in range(depth):
                if x in (0, width - 1) or z in (0, depth - 1):
                    put(x, 0, z, "minecraft:mossy_stone_bricks")
                    for y in range(1, height):
                        put(x, y, z, "minecraft:glass")
                put(x, height - 1, z, "minecraft:glass")
        for x in (0, width - 1):
            for z in (0, depth - 1):
                fill(x, x, 1, height - 1, z, z, "minecraft:stripped_spruce_log[axis=y]")
        for x in range(width):
            put(x, height - 1, 0, "minecraft:spruce_planks")
            put(x, height - 1, depth - 1, "minecraft:spruce_planks")
        door_x = width // 2
        # Two separately closable doors, a covered vestibule and a clear walk.
        for z in (-2, 0):
            for half, y in (("lower", 1), ("upper", 2)):
                put(door_x, y, z, "minecraft:spruce_door[facing=south,half=" + half +
                    ",hinge=left,open=false,powered=false]")
        for z in (-2, -1):
            for x in range(door_x - 1, door_x + 2):
                put(x, 0, z, "minecraft:spruce_planks")
                put(x, 3, z, "minecraft:spruce_slab[type=bottom,waterlogged=false]")
                if x != door_x:
                    fill(x, x, 1, 2, z, z, "minecraft:glass")
        for z in range(1, depth - 1):
            put(door_x, 0, z, "minecraft:spruce_planks")

        if key == "homestead-hamsters":
            for x in (3, 7):
                put(x, 1, 5, BED)
                # Small shaded sleeping alcoves, with open fronts and no fire.
                fill(x - 1, x + 1, 1, 2, 6, 6, "minecraft:oak_planks")
                fill(x - 1, x + 1, 3, 3, 4, 6, "minecraft:spruce_slab[type=bottom,waterlogged=false]")
                put(x, 3, 6, "minecraft:lantern[hanging=false,waterlogged=false]")
            for x, z in ((2, 2), (8, 2), (2, 4), (8, 4)):
                put(x, 1, z, "minecraft:oak_slab[type=bottom,waterlogged=false]")
                put(x, 0, z, "minecraft:moss_block")
            for x, z, flower in ((1, 1, "dandelion"), (9, 1, "cornflower"), (1, 7, "poppy"), (9, 7, "azure_bluet")):
                put(x, 0, z, "minecraft:grass_block")
                put(x, 1, z, "minecraft:" + flower)
            required_support = [[x, 0, z] for x in range(1, 10) for z in range(1, 8)
                                if (x, 0, z) not in blocks]
            nest_spots = [[3, 1, 5], [7, 1, 5]]
            spawn_positions = [[3.5, 1, 3.5], [7.5, 1, 3.5]]
        else:
            # Existing living trees may supply these forms only after exact
            # native survey; this relative source never clears a standing tree.
            for x, z, top in ((3, 4, 8), (11, 10, 10)):
                fill(x, x, 1, top, z, z, "minecraft:oak_log[axis=y]")
                for y, dx in ((4, 1), (6, -1), (top - 1, 1)):
                    fill(x - 2, x + 2, y, y, z, z, "minecraft:oak_log[axis=x]")
                    fill(x, x, y, y, z - 2, z + 2, "minecraft:oak_log[axis=z]")
                    put(x + 2 * dx, y + 1, z, "minecraft:moss_carpet")
                fill(x - 2, x + 2, top + 1, top + 1, z - 2, z + 2, LEAVES)
            # Two roofed elevated nesting boxes with open fronts and landing
            # platforms. They are shelter, not falsely named modded nest blocks.
            nest_spots = []
            for x, z, y in ((3, 9, 5), (10, 3, 8)):
                fill(x - 1, x + 1, y, y, z - 1, z + 1, "minecraft:spruce_planks")
                fill(x - 1, x + 1, y + 1, y + 2, z + 1, z + 1, "minecraft:oak_planks")
                for side in (x - 1, x + 1):
                    fill(side, side, y + 1, y + 2, z, z + 1, "minecraft:oak_planks")
                fill(x - 1, x + 1, y + 3, y + 3, z - 1, z + 1, "minecraft:spruce_slab[type=bottom,waterlogged=false]")
                put(x, y + 1, z, "minecraft:moss_carpet")
                nest_spots.append([x, y + 1, z])
            # Separated branches leave genuine airspace for gliding.
            for x in range(5, 10):
                put(x, 4, 6, "minecraft:oak_log[axis=x]")
            for x, z in ((1, 1), (13, 1), (1, 13), (13, 13)):
                put(x, 1, z, "minecraft:lantern[hanging=false,waterlogged=false]")
            required_support = [[x, 0, z] for x in range(1, 14) for z in range(1, 14)
                                if (x, 0, z) not in blocks]
            spawn_positions = [[3.5, 1, 6.5], [10.5, 1, 10.5]]
        habitats.append({
            "id": key, "anchor": None, "placement_status": "UNSURVEYED_SOURCE_ONLY",
            "bounds_relative": [[0, 0, -2], [width - 1, height - 1, depth - 1]],
            "blocks": [[*pos, state] for pos, state in sorted(blocks.items())],
            "required_existing_air": [[x, y, z] for x in range(1, width - 1)
                                      for y in range(1, height - 1) for z in range(1, depth - 1)
                                      if (x, y, z) not in blocks] + [[door_x, y, -1] for y in (1, 2)],
            "required_existing_solid_support": required_support,
            "nest_spots_relative": nest_spots,
            "residents": {"entity_type": entity, "initial_count": 2, "managed_admission_ceiling": 4,
                          "spawn_positions_relative": spawn_positions, "owner_uuid": None,
                          "assign_owner": "Owner's normal taming interaction only",
                          "NoAI": False, "Invulnerable": False,
                          "repeat_policy": "Inspect stable managed tags, bed links and UUIDs first; never duplicate or refill missing pets automatically",
                          "bed_recovery_boundary": "Hamster native bed recovery creates a new UUID and may lose external entity tags. Hold the slot for observed owner/bed reconciliation; never fabricate a respawn or silently rebind."},
        })
    return {"format": 1, "status": "SOURCE_PROPOSAL_NOT_PLACED", "world_write_authority": "NONE",
            "integration_owner": "Build It! / master", "absolute_coordinates": False,
            "initial_total": 4, "managed_admission_ceiling_total": 8,
            "population_boundary": "Admission budgets only. Breeding/natural spawns do not have a global automatic cap. No culling or NoAI.",
            "preconditions": ["Exact installed mod/config hashes and native registry confirmed",
                              "Master lease, verified checkpoint, empty roster and current terrain/clearance survey",
                              "All body/flight/support and structure-before masks accepted without clearing unrelated terrain",
                              "Habitat placed and native containment/visual checks passed before any resident",
                              "Stable managed tags/UUIDs; own pets only; no invented player ownership"],
            "habitats": habitats}


if __name__ == "__main__":
    print(json.dumps(build_habitats(), indent=2))
