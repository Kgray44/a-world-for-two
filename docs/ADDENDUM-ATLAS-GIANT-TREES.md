# A World for Two: Control Room World Atlas & Giant Trees

**Repository:** https://github.com/Kgray44/a-world-for-two

Expand the current full-scope implementation with a lightweight, searchable, live world map integrated directly into the browser-based Control Room dashboard, plus carefully selected giant-tree content.

Preserve all earlier features and the selected Distant Horizons + SeedGen architecture. Do not reintroduce Roxy or Voxy.

## 1. Control Room: World Atlas

Build a dedicated **World Atlas** page.

**Preferred mapping backend: squaremap**, using a verified NeoForge 1.21.1 release.

Investigate The Explorer's Friend as a lighter or more compatible alternative, particularly for rendering modded blocks.

Favor established rendering software rather than building a custom world renderer.

### Required capabilities

- Real browser-viewable world map
- Overworld, Nether, and End maps
- Pan, zoom, search, and coordinates
- Live player locations and facing direction
- Player selection and centering
- Named, searchable waypoints
- Click-to-create waypoints
- Editable markers, categories, icons, and colors
- Shared and private waypoint collections
- Real-time updates for newly explored or changed areas
- Searchable locations and discovered structures
- Support for markers from selected modded structures
- Selected entity and named-pet markers in loaded chunks
- Moving trains, ships, and airship positions where reliable APIs exist
- Death and grave recovery markers
- Protected territory and claim boundaries
- Waypoint synchronization with Xaero's when a verified adapter is available
- Teleport selected player to an authorized, safely validated map location
- Teleport to saved waypoints or another player
- Save previous position for convenient return
- Export/import waypoint collections

### Data accuracy

Use genuine world and server data.

Distinguish:
- Loaded entities and objects
- Persisted known locations
- Discovered world structures
- Map-rendered chunks
- Unexplored terrain
- Distant Horizons SeedGen-generated visual LODs

Do not present predictions or unverified generated structures as confirmed locations.

Do not trigger expensive full-detail chunk generation merely because a user pans or searches the map.

Do not scan the entire world repeatedly to find objects.

Use event-based indexing and targeted queries where possible.

### Lightweight operation

- Prefer a 2D tile-based browser map
- Cache map tiles
- Render changed regions incrementally
- Avoid unnecessary world scans
- Avoid always-running 3D rendering
- Rate-limit client updates
- Poll player positions approximately every 2–5 seconds, configurable
- Update less critical markers on events or longer intervals
- Pause expensive map rendering during server performance problems
- Cap map storage and tile cache usage
- Avoid loading new world chunks solely for map display
- Prioritize Minecraft TPS over map freshness
- Load the World Atlas interface only when viewed

Instrument CPU, RAM, disk, and server tick overhead.

### Teleportation security

- Administrator-only operation
- Require explicit confirmation
- Validate selected player and destination dimension
- Check world borders and destination safety
- Load only the minimal required destination chunks
- Prevent suffocation, dangerous falls, or unsafe spawn placement
- Preserve a return location
- Log all teleportation actions
- Never expose command execution publicly

Keep Control Room accessible only through its authorized local management interface by default.

Do not expose it through the public Minecraft connection tunnel.

### Integration

Use a small NeoForge server-side bridge only where existing APIs are insufficient.

Provide access to genuine player, waypoint, structure, and selected moving-entity data without unnecessary tick-time overhead.

Keep client-only mapping data separate from authoritative server data.

Implement reliable waypoint synchronization rather than falsely claiming that all Xaero's client waypoints are automatically visible.

## 2. Giant trees

Investigate and integrate the best compatible selection of:

1. **Giant Tree** — preferred for player-grown enormous trees and treehouse construction
2. **Tree Giant** — preferred candidate for naturally generated biome-specific giant trees
3. **L-Trees: Giant Trees** — experimental world-tree candidate
4. **Dynamic Trees** — advanced alternative
5. **Dynamic Trees - Terralith**
6. **Dynamic Trees - Regions Unexplored**

Prioritize Giant Tree for controlled, player-created landmark trees.

Investigate whether Tree Giant can generate enormous trees sparsely without interfering with Terralith, Tectonic, Regions Unexplored, and Distant Horizons SeedGen.

Do not install overlapping tree world-generation systems without compatibility tests.

Avoid excessive tree size, generation frequency, and block-update overhead.

Test growth, lighting, leaf behavior, terrain generation, server restarts, and save integrity.

Ensure that tree generation does not produce serious lag spikes or excessive cache/storage growth.

The goal is rare, breathtaking giant trees and the possibility of building a beautiful multi-level treehouse.

## 3. Control Room performance requirements

This project must remain lightweight despite its extensive features.

The host machine is a 32 GB Windows gaming laptop that must simultaneously run the dedicated server and Minecraft client.

Provide configurable map-rendering budgets and pause/resume controls.

Expose:

- Map-rendering CPU usage
- Map cache size
- Background rendering queue
- Player tracking refresh rate
- Structure-index size
- Last map update time
- Map renderer pause/resume
- Cache cleanup controls

Maintain the existing server optimization architecture.

The implementation must not sacrifice server responsiveness merely to keep the browser map updated.

## 4. Final requirements

Integrate the World Atlas into the existing Control Room application.

Add selected mods to Packwiz and the canonical compatibility inventory.

Include tests for map navigation, waypoint management, live player tracking, safe teleportation, persistence, permissions, giant tree generation, and server performance.

Do not report unimplemented functionality as operational.

**Desired experience:** KG opens Control Room, views the shared world map, sees both players and known landmarks, places new waypoints, monitors the world, and safely administers the server from one lightweight browser interface.

Implement this as part of the existing complete A World for Two build.