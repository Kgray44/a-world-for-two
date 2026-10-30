# Tortuga and the entire build — established schematic style

30 October 2026. These two maps use the same muted palette, flat geometry,
Georgia headings and paper frame as the previous Tortuga construction maps.

- `tortuga-current-overhead.png`: full north-bank Tortuga, original district,
  western and eastern compounds, surrounding greenery and harbor footprints.
- `whole-build-current-overhead.png`: both towns, all seven vessel structures,
  fountain, castle, watermill, bridges, Hypertube entrances and KG's zipline.
- `tortuga-building-index.csv`: names, districts, purposes and coordinates for
  all 118 inventoried Tortuga properties.

The base is classified from real saved top-surface blocks in the immutable
096bdd retained backup, not colors sampled from a Minecraft screenshot or
squaremap image. `surface-data.json` records the archive, region and image hashes.
Unknown saved columns remain the neutral unknown category.

The retained snapshot was saved 30 October 2026 at 11:55 a.m. EDT (15:55 UTC).
Player changes after that snapshot are not included in the saved-surface base.

The city geometry comes from the 118-property completed-building inventory and
its construction sources. Ground and planted overlays retain actual placement
receipts. Ship footprints use the actual admitted placement documents. Geometry
is a schematic projection and does not represent interior furnishings, live
entity locations or gameplay/artistic acceptance.

KG's zipline is drawn from its saved 15-knot/14-link entity graph. The whole polyline
is displayed on the full map and clipped naturally to the detailed city map.
This replaces the older guessed straight guide. The existing white bridge is
shown in its current location; its source-only relocation is not drawn as built.

Rendering performs no Minecraft commands, runtime writes or save mutations.
`map-evidence.json` retains rendered hashes and geometry provenance.
