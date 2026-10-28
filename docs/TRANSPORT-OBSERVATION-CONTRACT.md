# Transport observation contract for Control Room and Atlas

**Availability: installed source in private candidate.51 / bridge0.6.37;
native capture has not yet been demonstrated.** The actual deployed JAR SHA is
`cb634e9c848b11d6f2cb90533de8f91779dc56b8420a37857ae9b2bf75bce2a6`.
The installed artifact contains the observer and passenger-schedule classes, and
the master source registers its lifecycle and console allowlist hooks. Revalidate
that identity at the read window; a class in a JAR is not a successful capture.
This artifact check was made19:37UTC; the master's subsequent candidate52
transition does not automatically qualify captures from the replacement artifact.
`compat/control-bridge/proposals/transport-commission-r1/TransportObservationSupport.java`
defines this contract. There is no transport HTTP endpoint or continuously updated position feed.
Do not turn missing receipts into an empty train list or successful diagnostics.

The console-only operation is `awfttransport snapshot <label>`, where label
matches `[a-z0-9_-]{1,32}`. Only master may enable/trigger the coordinated read
window. The observer runs on the server thread, registers no tick listener,
requests no chunks/tickets, discovers no graph through world reads, moves no
player/item and performs no setup or world mutation.

## Receipt custody

The result family is
`H/dashboard/settlement/transport-observation-result-<UUID>.json` with adjacent
`.json.complete` containing the exact64-character SHA-256 of the closed JSON.
`H` is the construction runtime identified in WORKSTREAMS. Terminal publication
uses existing `NativeJournal`; files are immutable and never overwritten.
Root `format` is `awft-native-transport-observation:1`.

Consumers authenticate the master-deployed helper/class/JAR and actual process
identity, then validate the marker and bounded JSON (maximum2MiB for this reader).
A matching marker alone is file custody, not proof that arbitrary JSON came from
Minecraft. Match `pid` and `process_started` to fresh existing server telemetry.
Apply the normal15second freshness threshold for a live view; older observations
may be labelled historical with their actual timestamp. Neither a stale receipt
nor an absent adapter is a live empty world. Failed capture may produce no receipt.

## Root fields

| Key | Meaning |
| --- | --- |
| `format`, `label`, `at` | Contract version, operator label and actual UTC capture time |
| `boot_id`, `pid`, `process_started` | JVM-local observation session and actual process identity |
| `candidate`, `bridge`, `world`, `game_time` | Declared parent candidate, checked loaded bridge version, actual save path and native game time; master authenticates installed pack custody separately |
| `players` | Actual connected-player observations, including other dimensions |
| `trains` | Native trains with available Overworld positions **inside** the bounded Copper Wren area |
| `train_position_scope` | `dimension`, `min_x`, `max_x`, `min_z`, `max_z`; currently Overworld X1288..1350, Z−1020..−910 |
| `native_registered_train_count` | Native registry train count before the area filter; capture refuses more than128 |
| `train_position_unavailable_count` | Registered trains lacking an available Overworld position; do not invent map markers |
| `ship_positions`, `airship_positions` | Explicit `{availability: unavailable, reason: ...}`; this observer calls no fleet/airship adapter |
| `stations`, `track_graph`, `tube_links`, `drives`, `cargo` | Scoped native diagnostic observations below |
| `world_mutated`, `owned_tickets` | Always false and0 for successful observer capture |
| `limits` | Point-observation limitations; no riding, native filler-shape, zipline-client, performance or owner acceptance |

## Player and train rows

Each player row contains `uuid`, `name`, `dimension`, `position` (actual X/Y/Z),
`chunk` (actual X/Z), `on_ground`, `health`, `hypertube_native_travel` and
`train_uuid`. Train UUID is null when the real root vehicle is not a valid native
Create carriage. The tube flag is the pinned mod's native persistent travel flag;
position changes alone do not establish riding. No zipline client-physics flag
is supplied by this server observer.

Train rows contain `uuid`, `position`, `speed`, `invalid`, `derailed`,
`double_ended`, `graph_id`, `station`, `player_passengers`, `forward_conductor`,
`backward_conductor`, `carriages`, `seats`, `schedule_present`, `schedule_paused`,
`schedule_completed`, `schedule_entry`, `schedule_cyclic`, `native_schedule_snbt`,
`schedule_condition_progress` and `schedule_condition_context`.
`seats` gives each carriage's native seat count, with−1 for an unavailable actual
carriage/contraption. `graph_id` and `station` may be null. These unavailable
values must not become zero seats, a stationary marker or a completed schedule.
Native schedule SNBT/context are bounded diagnostic custody, not user-facing labels.

## Diagnostic rows

Station rows always identify `position` and `available`. Available rows add
`target`, `direction`, `valid_track`, `station_point`, `station_uuid`, `name`,
`graph_id` and `present_train`; the latter four may be null. The station chunk and
target must already be loaded before target-track reads. Graph lookup uses the
existing GlobalStation object and in-memory native graph nodes, bounded to1024
visited nodes. `track_graph.status` is one of `unavailable`,
`stations_have_no_shared_graph`, `native_edge_node_missing`,
`bounded_graph_walk_incomplete`, `station_nodes_connected` or
`station_nodes_disconnected`. It does not establish passenger navigation.

Each of six tube rows has `from`, `to`, `available`; available rows add
`stored_reciprocal` and, when a native Bezier exists, `uuid` and `distance`.
This does not validate every native filler collision shape or a real trip.
Drive rows contain `position`, `available` and, when available, native `rpm`,
`overstressed`, `needs_update` and `block_state`.

`cargo.scope` is `copper_wren_fixed_v1`, with `complete`, `stores`, `dropped`,
`dropped_query_complete`, `aliased_transit_objects` and `extractor_filter`.
Store rows identify `role`, `position`, `available` and actual nonempty `items`.
Container rows also report `slots`; tube rows report `in_transit` and, when
present, `animation_id`, `path_index`, `waiting_at_destination`. Item rows contain
`slot`, `item`, `count`, `components`, `plain`, `native_item_class` and
`has_captured_blaze` (the actual registered item getter, never inferred from NBT).
The extractor filter is a template excluded from goods. This is a declared local
inventory scope, not every inventory or item in the world.

## Existing telemetry and timing samples

Current `H/dashboard/server-metrics.json` remains the existing native timing/player
source (`awft-metrics:1`); it does not become a train/fleet position adapter.
`tools.transport_performance` may read its distinct nonoverlapping intervals in a
master-coordinated30..120second window, producing
`H/staging/<owned-name>/native-timing-intervals.json` and `manifest.json`.
The manifest identifies actual PID/start/CWD, declared phase, freshness/errors,
pack identity and tick-weighted mean MSPT. Interval means are not per-tick
percentiles. No transport timing profile has been collected by this workstream.

Fleet and airship position integration belongs to the corresponding owners and
master. Static authored ship coordinates, proposed routes, block counts and
unavailable native carriages must never be presented as live vessel positions.

## Passenger observation audit

`tools.transport_passenger_audit` reads genuine canonical observer results and
their exact completion markers. It sends no commands and simulates no passenger.
Master supplies the actual authenticated KG and Sera UUIDs; the full connected
roster must contain both identities throughout the observed sequence. Captures
use one actual world/candidate/bridge/PID/start/boot, advancing native ticks,
at most three minutes between stages and fifteen minutes overall.

For `train`, pass seven files in this order: mill platform, both boarded at the
mill, outbound motion, actual orchard stop attachment, inbound motion, actual
mill stop attachment, both off-train on the mill platform after finite completion.
The native train/graph/station identities stay fixed, both real conductor
directions and passenger counts are observed, and the exact three-entry native
schedule contains20second dwell plus two-player conditions, then zero-player
unloading. Create6.0.10 resets `currentEntry` to0 when finite completion pauses;
the observed sequence is0/0/1/1/2/2/0. Only its known serialized `Progress` field
may vary within0..2; changed instructions, conditions or unknown progress refuse.

For `hypertube`, pass eight files: ground at mill, two native in-tube observations
in different Z chunks, ground at orchard; then the same four stages in reverse.
Both real players must have the native tube flag and move in the proper direction;
all six unique stored reciprocal eight-metre links remain unchanged. X-only
chunk changes cannot establish crossing the straight tube's Z boundary.

```powershell
python -B -m tools.transport_passenger_audit train --home H `
  --kg-uuid ACTUAL_KG_UUID --sera-uuid ACTUAL_SERA_UUID FILE0 FILE1 FILE2 FILE3 FILE4 FILE5 FILE6
python -B -m tools.transport_passenger_audit hypertube --home H `
  --kg-uuid ACTUAL_KG_UUID --sera-uuid ACTUAL_SERA_UUID FILE0 FILE1 FILE2 FILE3 FILE4 FILE5 FILE6 FILE7
```

Eleven focused synthetic tests pass. No genuine passenger session was captured.
A successful audit proves only its observed states after provenance review.
Point captures cannot exclude movement/disconnections between captures;
`train_uuid=null` also does not prove dismounting from every other vehicle.
Continuous riding, walking/boarding ergonomics, filler collision safety, zipline
braking and safe arrival, wider intended railway route, restart and KG/Sera's
acceptance remain separate runtime requirements.
