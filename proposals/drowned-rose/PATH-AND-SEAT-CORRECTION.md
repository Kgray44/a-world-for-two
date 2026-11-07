# Native path search and persistent Handcrafted seat correction

The active0.1.3 test still produced gathering timeouts and no performance.
At03:50:24UTC,409 of418 refusals were outside_transit. Rejected nodes were
native shortcuts over real chairs/tables or through the decorative column,
not additional safe floor cells. Accepting all of them would be wrong.

`SurveyedPaths` uses the real native WalkNodeEvaluator for geometry, floor
height, headroom and step/jump decisions. It filters its neighbor candidates
to the same finite269 admitted cells BEFORE the native PathFinder A* chooses
a route. Cardinal expansion prevents cutting an excluded furniture corner.
Search is bounded to2048 visits and the already-loaded four-chunk region.
The existing native navigation follows the resulting path at the same speed;
the post-search containment check remains. No new graph cells, furniture
edits, ordinary teleports, force-loading or replacement NPCs are introduced.

The actual native A* regression on a synthetic floor passes: an unconstrained
shortest path crosses excluded furniture; constrained search finds a longer
approved aisle; a completely blocked aisle remains unreachable; diagonal
furniture corner cuts are excluded. This is not a saved-world path test.

Both missing residents, Oona Kelp and Dara Moss, were absent from all1,391
entity rows including passengers in authenticated e9d33f, but present in
earlier authenticated42bdb5. Their retained ledger destinations were chairs.
Pinned Handcrafted4.0.3 bytecode confirms its original seat type calls
EntityType.Builder.noSave(). A mob riding that unsaved root vehicle cannot
be relied on to survive normal chunk serialization. Stop-only dismounting
does not solve the chunk-unload case.

The correction registers ONLY `awft_tavern:persistent_seat`, a saveable
Handcrafted Seat subclass. Its public native constructor installs the native
level callback, which derives chair shape from the actual SittableBlock on
position/load. Native passenger attachment, facing, dismount, collision and
seat lifecycle remain inherited. Parent and original patron Passenger NBT
serialize normally; the subclass adds the resident UUID and a short orphan
cleanup. A client-only NoopRenderer keeps the furnishing as the visible chair.
The global Handcrafted type and other players' seats are unchanged.

Keep this adapter installed while its persistent seats exist. A future removal
or downgrade must first dismount managed patrons and save them as ordinary
entity roots, or use the matching prechange world backup; removing a registered
vehicle type from a saved world would risk its passenger records.

The two original gzipNBT payloads were extracted byte-for-byte from42bdb5,
preserving UUID/name/skin/inventory and every original typed NBT field. Native
CompoundTag serialization also produced reviewable SNBT. The private packet
is `D:\A World for Two\staging\drowned-rose-source-20261029\recovery-original2-42bdb5`.
No restoration occurred in this source chat. Root alone may restore them after
the fixed seat type is verified, a fresh authoritative whole-world census
proves both absent (including passengers/player UUIDs), and actual native body
clearance is checked. Never reset the ledger or substitute new identities.

Startup, active native detours, gathering/start of actual Monkey Island,
client riding pose, seat save/unload/reload with all45 retained, whole-tune
audio, two clients and measured tick cost still require real runtime evidence.
