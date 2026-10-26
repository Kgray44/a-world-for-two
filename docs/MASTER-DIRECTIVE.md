# CODEX MASTER BUILD DIRECTIVE
# A World for Two

**Repository:** https://github.com/Kgray44/a-world-for-two

**Reference repository:** https://github.com/Kgray44/kg-minecraft-pack

**Project:** A World for Two

**Goal:** Design, develop, integrate, test, and deliver a complete, highly optimized, beautiful Minecraft modpack and local server management system for KG and Sera.

This is a full implementation task, not a request for an architectural proposal.

## 1. Project vision

Create an exceptionally beautiful, cozy, romantic, mechanically sophisticated Minecraft experience for two people.

The experience should combine:

- Cozy cottages, homesteading, furniture, kitchens, cooking, gardening, and farming
- Adorable wildlife, pets, frogs with leaf umbrellas, hedgehogs, and ideally flying squirrels
- Extraordinary terrain, mountains, valleys, rivers, wilderness, and beautiful biomes
- An enormous visible world extending far beyond Minecraft's normal render distance
- Create machinery, automation, trains, railway infrastructure, and fascinating engineering
- Functional ships, sailboats, flying machines, and airships
- Exploration, dragons, cannons, and one good firearms mod
- Warm cinematic graphics and high-quality shaders
- Reliable multiplayer for KG and Sera
- Excellent performance, clean mod synchronization, and easy administration

The finished system should be more than a collection of mods. It should be an integrated, reproducible, maintainable platform.

**Absolutely do not sacrifice the atmosphere or core features merely to reduce the number of installed mods. However, do not introduce instability for the sake of hitting an arbitrary mod count.**

## 2. Development requirements

The new repository is the sole development target.

Inspect the previous `kg-minecraft-pack` repository to understand the established Packwiz/Prism workflow, automatic launcher updates, instance export, and GitHub Pages publishing.

Do not modify the previous repository.

Use:

- Minecraft Java Edition 1.21.1
- NeoForge 21.1.x, selecting and pinning a tested compatible release
- Java 21
- Prism Launcher
- Packwiz as the canonical modpack definition
- GitHub for source control and releases
- A dedicated Windows NeoForge server
- A lightweight custom web-based server dashboard

Initial NeoForge candidate: 21.1.255, subject to compatibility verification.

Pin all dependencies to exact tested versions.

Do not blindly install the newest file for every mod.

## 3. Mandatory mod inventory

The following is the requested inventory.

Every item must appear in a machine-readable compatibility manifest and a human-readable report.

Status must be one of:

- Integrated and tested
- Integrated but awaiting runtime validation
- Alternative selected
- Incompatible, with evidence
- Unresolved, with investigation details

Do not silently omit requested mods.

### A. Cozy living, farming, kitchens, and furniture

Required investigation and integration targets:

1. Farmer's Delight
2. Kaleidoscope Cookery
3. Handcrafted
4. Supplementaries
5. Macaw's Furniture
6. Macaw's Windows
7. Macaw's Doors
8. Macaw's Roofs
9. Macaw's Bridges
10. Macaw's Fences and Walls
11. Macaw's Trapdoors
12. [Let's Do] Farm & Charm
13. [Let's Do] Vinery
14. Comforts

Also research suitable compatible additions for:

- Cozy bedrooms and couples' homes
- Chairs and genuinely usable furniture
- Picnics, camping, and outdoor living
- Decorative kitchens and appliances
- Greenhouses and gardening
- Attractive lighting
- More farming and food variety
- Cute home accessories
- Optional weather and seasonal ambiance

Avoid excessive overlap or duplicated mechanics.

### B. Wildlife and adorable creatures

Required:

1. Ribbits, especially its umbrella-carrying frogs
2. Naturalist, including hedgehogs
3. Critters and Companions

Research and prioritize:

4. Flying squirrels
5. More cute forest animals
6. Ducks, otters, butterflies, and other small creatures
7. Wildlife behavior and ambient immersion
8. Appropriate animal animations and sounds

Investigate flying-squirrel mods thoroughly. If none is suitable for this version, document the situation and the best alternatives.

Keep spawn densities sensible. The world should feel alive without overwhelming the server with entity simulation.

### C. World generation, biomes, and exploration

Primary targets:

1. Tectonic
2. Terralith
3. Regions Unexplored

Alternatives or supplementary candidates:

4. Oh The Biomes We've Gone
5. Nature's Spirit
6. Compatible structure-generation mods
7. Enhanced villages and settlements
8. Interesting ruins, landmarks, and explorable locations
9. Better rivers, caves, and natural scenery
10. Appropriate atmospheric and environmental details

Create several throwaway world-generation test worlds before committing to one terrain configuration.

Verify terrain compatibility, biome distribution, climate transitions, world-generation performance, and structure placement.

Our world must feel dramatically different from vanilla Minecraft.

Investigate raising the vertical world-height limit, but do not enable it in the permanent world if doing so introduces significant compatibility, performance, serialization, or rendering risks.

Document the outcome.

### D. Create engineering and transportation

Required:

1. Create
2. Create: Steam 'n' Rails, using the verified 1.21.1 NeoForge port
3. Create: Deco
4. Create: Crafts & Additions
5. Create: Central Kitchen
6. Create: Slice & Dice
7. Create: Ornithopter Glider
8. Create Aeronautics
9. Sable, where required by Aeronautics
10. Create Big Cannons
11. Ritchie's Projectile Library, where required

Investigate additional compatible Create addons related to:

- Trains and railroad infrastructure
- Steam engines and mechanical components
- Decorative machinery
- Electrical systems
- Food processing
- Airships, aircraft, and propulsion
- Logistics and transportation

Create trains are a particularly important feature and must receive explicit multiplayer testing.

Create Aeronautics must be investigated and tested with Sable, Create, shaders, trains, and cannon systems.

Where necessary, select stable releases rather than alpha or beta versions.

### E. Ships and nautical exploration

Required:

1. Small Ships

Research other compatible options for:

- Real sailing mechanics
- Sailboats and larger ships
- Ship upgrades and navigation
- Dockyards and harbors
- Naval decoration
- Ship-mounted cannons
- Ocean exploration and interesting islands

Avoid duplicate ship mods unless they add meaningfully different functionality.

### F. Adventure, dragons, and weapons

Required investigation:

1. Bluedude Dragons, or a better compatible How to Train Your Dragon-inspired alternative
2. Create Big Cannons
3. TaCZ unofficial NeoForge port, or one proven alternative firearms mod

Use only one main firearms system.

Investigate applicable gun-pack compatibility requirements.

Keep the overall world primarily cozy and adventurous rather than turning it into a combat-focused survival pack.

### G. Player interaction and immersion

Required:

1. Cinematic Interactions
2. Investigate Immersive Interactions as an alternative or complementary mod
3. Essential Mod for optional hosted-world fallback

Also investigate:

4. Suitable player seating and interaction animations
5. Appropriate ambient audio enhancements
6. Subtle environmental atmosphere enhancements

### H. Specifically mentioned unresolved mods

Investigate these names exactly rather than guessing:

1. Flame
2. Kaleidoscope, determining whether the intended project is Kaleidoscope Cookery or a separate mod
3. Derivative shader

For each, determine the correct project identity, supported Minecraft version, and suitability.

### I. Shaders and graphics

Required shader investigation and integration:

1. BSL Shaders
2. Complementary Reimagined
3. Complementary Unbound
4. Derivative
5. Other high-quality, soft, warm shader alternatives

Required rendering infrastructure:

6. Sodium
7. Iris

Create at least two working graphics profiles:

- High Quality: designed around KG's RTX 5070 laptop
- Balanced: for Sera or lower-performance clients

Do not assume Sera's hardware specifications.

Shader differences must never create a server mod synchronization mismatch.

Test shader compatibility with Create Aeronautics, moving contraptions, translucent entities, ships, and distant terrain.

## 4. Extremely long-distance terrain rendering

This is a major project requirement.

KG wants breathtaking distant mountains, valleys, and terrain visible without physically traveling to every location first.

Investigate and implement the best verified option.

### Candidate A: Voxy ecosystem

- Voxy
- Roxy
- Voxy SeedGen
- LOD Server Support, where applicable

Use the specific Roxy/Voxy/version combinations documented as compatible.

### Candidate B: Distant Horizons ecosystem

- Distant Horizons
- Distant Horizons SeedGen

This is a high-priority alternative because SeedGen supports generation based on the world seed, including noise-based terrain systems such as Tectonic and Terralith.

### Candidate C: Additional generation options

- LODgen
- Other trustworthy compatible distant-terrain generation systems

Compare:

- NeoForge 1.21.1 compatibility
- Tectonic/Terralith/biome-mod fidelity
- Multiplayer behavior
- Whether unexplored terrain becomes visible
- Shader compatibility
- CPU, RAM, VRAM, and disk requirements
- World-generation speed
- Client/server installation needs
- Crash and corruption risk
- Performance while Create Aeronautics is operating

Do not combine incompatible client LOD rendering systems.

Choose one primary tested solution and preserve a documented fallback.

Do not mistake visual LOD generation for full saved Minecraft chunk generation.

Create automated screenshot-based and coordinate-based comparisons between distant terrain and fully generated terrain.

The final system should aim for substantial distant visibility without the user needing to explore everything personally.

## 5. Client performance optimization

Investigate and install appropriate versions of:

1. Sodium
2. ImmediatelyFast
3. Entity Culling
4. More Culling
5. Dynamic FPS
6. FerriteCore
7. ModernFix
8. Iris

Also investigate additional proven optimization mods where valuable.

Do not install redundant or conflicting renderers.

Benchmark startup time, memory consumption, frame rates, frametime consistency, terrain streaming, and shader performance.

## 6. Dedicated server optimization

Required investigation and installation:

1. Lithium
2. FerriteCore
3. ModernFix
4. Chunky
5. spark

Also investigate:

6. C2ME
7. ServerCore or an equivalent compatible optimization mod
8. ScalableLux
9. Alternate Current
10. FastSuite
11. Clumps
12. Let Me Despawn
13. Other genuinely effective NeoForge server optimizations

C2ME must undergo particularly careful compatibility testing with custom world generation and SeedGen. Do not enable it if it causes errors or instability.

Measure actual improvements instead of assuming every optimization mod improves performance.

Use sensible Java 21 garbage collection configuration, with profiling before applying elaborate JVM arguments.

Prioritize sustained 20 TPS and low tick-time variance with two active players.

## 7. Windows hosting environment

The host is a Gigabyte AERO X16 Windows laptop with:

- Ryzen AI 7 350
- NVIDIA RTX 5070 laptop GPU
- 32 GB RAM
- A secondary 2 TB WD_BLACK NVMe drive mounted as D:

The user is reserving approximately 100 GB on D: for this project.

Default installation root:

`D:\A World for Two\`

Do not format, repartition, delete unrelated files, or assume the allocated space is empty.

Create organized directories for:

- server
- world
- dashboard
- configs
- backups
- logs
- caches
- packwiz
- instances
- exports
- temporary staging

Start with 8 GB maximum Java heap for the server, 8 GB for KG's client, then tune based on measurements.

Monitor disk space and provide alerts when free space becomes insufficient.

Ensure pre-generation and LOD caches cannot silently fill the drive.

Never overwrite the permanent world without explicit owner approval.

## 8. Custom browser-based server dashboard

Build a lightweight, polished server management application named:

**A World for Two: Control Room**

This is a mandatory deliverable.

The application must run locally on Windows and be opened using a normal web browser.

Proposed address:

`http://127.0.0.1:8765`

Create a dedicated launch script that starts the management backend, opens the browser dashboard, and optionally starts the Minecraft server.

Prefer a minimal local backend and a lightweight responsive frontend.

A Python/FastAPI backend with psutil and a small vanilla JavaScript frontend is acceptable, but choose the simplest reliable design.

Avoid Electron, unnecessary services, heavyweight databases, cloud requirements, and large frontend frameworks.

SQLite is acceptable for historical metrics and application state.

### Dashboard: Overview

Display:

- Server online/offline/starting/stopping state
- Uptime
- Current TPS
- MSPT
- Tick-time history
- Connected players
- Maximum players
- Server CPU usage
- Server memory usage
- JVM heap usage where available
- Available system RAM
- Host CPU and RAM utilization
- Disk usage and remaining project space
- Current Minecraft/NeoForge version
- Current modpack version
- World name and seed visibility control
- Current server render and simulation distances
- Latest backup
- Connection tunnel status
- Recent warnings and errors

Use genuine metrics from verified sources. Never display guessed TPS or simulated data as live telemetry.

If standard RCON or diagnostic tools cannot provide particular metrics, implement a lightweight NeoForge server-side metrics bridge or mark those metrics unavailable.

### Dashboard: Performance

Include:

- Live charts
- Historical TPS/MSPT graphs
- Per-process CPU and RAM graphs
- JVM garbage collection statistics
- Loaded chunk counts where available
- Entity counts where available
- Dimension activity where available
- Diagnostic sampling intervals
- Performance alerts
- spark integration
- Easy export of performance reports

Keep collection overhead small.

### Dashboard: Optimization

Create a dedicated page with understandable settings for:

- View distance
- Simulation distance
- Player count
- Entity activation and simulation settings where supported
- Mob spawn settings
- Chunk generation and pre-generation limits
- Create-specific performance settings
- Aeronautics/Sable performance limits
- Java heap configuration
- Garbage collection settings
- Backup scheduling
- Autosave settings
- Relevant optimization-mod configuration files

Display recommended values alongside current values.

Mark every option as:

- Live-changeable
- Requires restart
- Experimental
- Dangerous to change after world creation

Include descriptions, validation, defaults, and a way to restore prior values.

### Dashboard: Server configuration

Manage:

- `server.properties`
- Whitelist
- Operators
- Gamerules
- Difficulty
- Spawn settings
- PvP
- Player limits
- View and simulation distances
- Relevant world configuration
- Mod configuration files through validated schema-aware forms

Allow advanced raw configuration editing, but include diffs, backups, and syntax validation.

### Dashboard: Players

Show:

- Online players
- Join/leave events
- Connection information
- Whitelist status
- Permission management
- Operator controls
- Kick functionality
- Safe command execution

Never expose Minecraft account credentials.

### Dashboard: Logs and diagnostics

Provide:

- Live server console output
- Searchable logs
- Warning/error filters
- Crash report viewer
- Diagnostic bundle export
- Clear explanations of common failures
- Mod loading and dependency error identification

### Dashboard: Backups

Provide:

- Scheduled world backups
- Manual backups
- Backup history
- Backup size and integrity status
- Restore from selected backup
- Retention settings
- Optional compression
- Disk-space alerts

Use safe save/flush procedures or controlled server shutdown where necessary for consistent backups.

Never restore while the server is writing to the active world.

### Dashboard: Connectivity

Display:

- Local server address
- Game port
- Playit tunnel status
- External join address where available
- Tailscale option
- Essential fallback instructions

The dashboard itself must not be exposed through the public Minecraft tunnel.

Default binding must be localhost only.

If remote dashboard access is later implemented, require authentication, explicit opt-in, and secure transport.

### Dashboard: Controls

Provide working controls for:

- Start server
- Graceful stop
- Restart
- View console
- Create backup
- Run health check
- Open server directory
- Open Prism Launcher
- Run compatibility validation
- Launch optimization diagnostics

Use clear confirmation dialogs for destructive operations.

Ensure the dashboard remains responsive during long-running server tasks.

## 9. Simple graphical mod management

This is another mandatory, high-priority feature.

Build a user-friendly **Mod Manager** page inside Control Room.

KG should be able to search for a mod, select it, and add it without manually modifying Packwiz files or distributing JARs.

Support:

- Modrinth search
- CurseForge lookup where authorized
- Manual project URLs
- Mod name search
- Installed mod inventory
- Mod version history
- Updates available
- Dependency information
- Required Minecraft version
- Required loader version
- Client/server side classification
- Conflict warnings
- Removal warnings
- Optional mods
- Mod profiles or feature groups

### Add-mod workflow

When KG selects a new mod:

1. Resolve its exact project identity.
2. Verify NeoForge/Minecraft compatibility.
3. Select a compatible release.
4. Resolve required dependencies.
5. Check conflicts and duplicate mod IDs.
6. Determine installation side.
7. Update the Packwiz definition.
8. Recalculate indexes and integrity hashes.
9. Stage changes in a temporary environment.
10. Run compatibility and dependency checks.
11. Show a proposed change summary.
12. Require approval before deployment.
13. Back up the server and create a rollback point.
14. Update the dedicated server as needed.
15. Publish compatible client changes for KG and Sera.
16. Require restart or relaunch when necessary.
17. Confirm pack and server synchronization.

The same workflow must support removing or upgrading mods, with more restrictive treatment of world-generation or content-bearing mods.

### Critical synchronization requirements

There must be ONE canonical mod manifest and ONE coherent release version.

Prevent accidental client/server version drift.

Do not deploy a new server mod set while clients are still configured against an incompatible version without communicating the change.

Support atomic manifest publication and release rollback.

Client-side-only mods should never be installed on the dedicated server.

Provide a **Sync Status** view explaining whether:

- KG's client matches
- Sera's client is known to match
- The server matches
- Updates are pending
- A relaunch is required

Do not claim a remote client has synced unless it has reported or otherwise demonstrated that state.

Keep the normal Prism + Packwiz pre-launch update workflow.

Provide convenient exports for both players.

Respect project distribution licenses and CurseForge restrictions.

## 10. Server startup and remote multiplayer

KG will host the dedicated server on the same laptop used to play Minecraft.

Provide convenient Windows scripts:

- Install
- Start World
- Stop World
- Open Control Room
- Update
- Backup
- Restore
- Repair Installation
- Diagnose

Normal usage should not require opening PowerShell or typing commands manually.

Investigate and integrate Playit for remote access, with Tailscale as an alternative.

Configure the appropriate firewall rule narrowly.

Keep online authentication enabled.

Whitelist KG and Sera.

Essential should remain available as a simpler fallback, not replace the primary server architecture.

Never expose RCON, dashboard administrative endpoints, or privileged monitoring ports to the public internet.

The initial setup can require explicit user input for account authorization, EULA acceptance, game credentials, and network-tunnel authentication.

Do not fabricate or bypass those requirements.

## 11. Project phases

Implement ALL five phases within this development effort.

### Phase 1: Stable foundation

Packwiz, Prism, NeoForge, world generation, cooking, homesteading, wildlife, and baseline optimization.

### Phase 2: Transportation and engineering

Create, trains, ships, gliders, compatible addons, and infrastructure.

### Phase 3: Advanced features

Aeronautics, Sable, cannons, dragons, interactions, and firearms.

### Phase 4: Graphics and distant terrain

Shaders, Voxy/Roxy investigations, Distant Horizons, SeedGen alternatives, and extensive render compatibility testing.

### Phase 5: Production experience

Server deployment, Control Room dashboard, mod management, backups, remote connectivity, client distribution, and final integration.

These are organizational stages within one complete build, not separate projects to postpone.

Implement each, preserve evidence, and deliver one cohesive system.

If a particular mod is demonstrably incompatible, preserve the reason and implement the closest reasonable alternative. Do not hide the change.

## 12. Testing and acceptance criteria

Create reproducible tests for:

- Fresh Prism instance import
- Automatic Packwiz synchronization
- Clean dedicated-server installation
- Server startup/shutdown
- Mod dependency validation
- Correct client/server mod separation
- New world generation
- Tectonic/Terralith biome generation
- Structure generation
- Kitchen and farming interactions
- Animal spawning
- Create contraption operation
- Train assembly and travel
- Small Ships behavior
- Aeronautics physics
- Cannons
- Dragon interactions
- Shader rendering
- LOD terrain generation without prior exploration
- Performance under exploration
- Server dashboard telemetry
- Server setting changes
- Backup and restore
- Mod add/remove/update
- Version rollback
- Remote player connection

Perform an extended stability test where resources permit.

Record actual CPU/RAM statistics, startup times, TPS/MSPT, and performance findings.

Do not invent benchmark measurements or claim multiplayer success without a real multiplayer test.

If local Windows access or multiple Minecraft accounts are unavailable, complete all feasible automated validation and explicitly document the remaining physical acceptance tests.

## 13. Required deliverables

The repository must contain:

1. Complete Packwiz manifests
2. A pinned compatibility inventory for every requested mod
3. Client/server mod classifications
4. All appropriate configuration files
5. Prism importable instance package
6. Client automatic update system
7. Dedicated NeoForge server setup
8. Windows startup and shutdown scripts
9. Custom Control Room web dashboard
10. Browser-based mod manager
11. Server optimization configuration
12. Distant-terrain rendering solution
13. Graphics profiles
14. Server backup and restore system
15. Remote multiplayer setup
16. CurseForge-compatible export where legally possible
17. Tests and benchmark tooling
18. Installation documentation
19. Recovery and troubleshooting documentation
20. Known compatibility limitations
21. Actual verification report
22. Clear final installation steps

Create a clean, understandable repository structure.

Maintain the source code and configurations in Git, but keep world saves, logs, downloaded proprietary JARs without redistribution permission, tokens, and large runtime caches out of source control.

## 14. Design standards

The dashboard should look like a polished modern application.

Visual direction:

- Warm, refined, cozy fantasy aesthetic
- Forest greens, warm neutral tones, restrained golden accents
- Clear typography
- Beautiful live charts
- Easy navigation
- Minimal visual clutter
- Responsive design
- Friendly but precise technical information

The interface must remain lightweight and fast.

Operational reliability is more important than decorative animations.

## 15. Final instructions

This is intended to be a long-term permanent world shared by KG and Sera.

Its integrity matters.

Do not wipe worlds, silently remove content mods, automatically overwrite configurations, or publish untested updates.

Implement the entire system as far as the execution environment allows.

Make reasonable engineering decisions autonomously and document them.

Do not repeatedly stop merely to ask whether to continue to the next already-authorized phase.

Use incremental checkpoints, commit meaningful milestones, validate changes, and recover from integration failures.

When finished, provide:

- What was actually implemented
- Every installed mod and its exact version
- Every requested mod not installed and why
- What tests passed
- What tests failed
- What remains untested
- How to install the server on D:
- How to open Control Room
- How KG starts the world
- How Sera joins
- How to add mods
- How updates and rollback work

**Definition of success:**

KG opens Control Room, starts the server, launches Prism, and plays.

Sera opens Prism, launches Minecraft, and joins the same beautiful world.

Both can explore extraordinary terrain, enjoy the cozy homestead, travel by train and ship, and use the intended modded features reliably.

The server can be monitored, optimized, backed up, updated, and maintained through a simple browser interface.

Everything should work together as one complete product, not as a collection of loosely connected experiments.

**Build A World for Two.**