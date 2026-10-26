# Control Room

Run `python -m control_room run --home "D:\A World for Two"` and open
`http://127.0.0.1:8765`. The dashboard is private and binds to loopback.

## Server and players

Start reports success after NeoForge reaches readiness. Stop flushes the saved world.
Players supports verified username lookup, whitelist edits, operator levels 0–4,
game mode and experience changes. Click a player for live coordinates, dimension,
available location preview and relevant actions. Permission changes preserve prior values.

The mobile sidebar closes on outside clicks. Changes require the local origin and
current session token. Explicit expired-token rejections refresh once; ambiguous
requests are not replayed. An old tab may need one reload after code updates.

## Atlas, storage and backups

The World Atlas uses real squaremap tiles, dimension selection, player centering,
named waypoints, shared/private collections, categories, search and discovered structures.
Bounded Open Parties and Claims overlays read existing claims without generating chunks.

Admin teleports require confirmation and a current online player. Surface mode uses
actual terrain height within one chunk; known-height mode searches near the supplied Y.
Hazards, water, obstruction, border violations and unsuitable Nether roofs are refused.
Return positions are retained. Native acceptance of the new landing path is pending.

Storage shows measured world, cache, backup, staging and source sizes with timestamps
and scan completeness. Background inventory keeps UI requests responsive. Pending
measurements are not zero. Logical and allocated sizes account for hardlinked files.

Backups stop writers, archive the saved world/configuration, verify file hashes and
resume if requested. Restore requires the exact identifier and preserves the previous world.

## Playit.gg

Connectivity integrates the installed Playit 1.0.x Windows service through its
official local named-pipe protocol. It shows service and agent state, linked status,
public address, local destination, active connections, traffic counters, notices
and bounded live activity. Start/Stop invoke the official installed CLI.

Stopping Playit disconnects remote users of all its tunnels; Minecraft continues
locally. Closing the dashboard leaves the service running. Account secrets stay in
Playit's own store; the dashboard does not reset or copy them or create a second agent.
Native stop/start passed on this host with zero active connections and the existing
account/tunnel retained. Remote player acceptance remains separate.

## Presentation

Menu artwork retains original uploaded bytes and preserves version history.
Camera and shader selections affect closed, explicitly owned local clients. Other
computers use their local settings. Graphics displays exact shader pins, style,
intended cost and Distant Horizons limitations; these are not FPS benchmarks.
