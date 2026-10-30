# Native settlement visual review

This small test helper is **excluded from Packwiz and release exports**. It can
save the real Minecraft framebuffer in an explicitly owned, signed-in test
instance connected normally to the loopback dedicated server. It neither renders
a substitute scene nor controls operating-system windows or game input.

Version 0.1.2 also accepts the explicitly authorized loopback staging server on
25575. It never connects to a public address. Poses remain confined to the local
settlement review envelope, including belowdecks; the target server is recorded
with each actual framebuffer capture.

Version 0.1.3 permits normal authenticated reconnect/disconnect and bounded
operator lighting commands on the private staging server only. This allows
construction between graphical reviews without repeatedly reloading the client.
The game and server retain normal account and permission enforcement.

Version 0.1.4 leaves a connection request pending until Minecraft reports game
loading complete, the startup overlay is absent, and the current screen is an
actual title or disconnected menu. It also requires no active world, player or
connection. The ready menu is passed to the normal connection API and recorded
in the request receipt. Readiness uses native state, with no sleep or elapsed-time
threshold. The existing one-second request polling interval is not a readiness
test.

The prior helper could issue its request from a loading frame. In the preserved
candidate32 attempt the server authenticated the test UUID, rejected configuration
as incompatible NeoForge, and the client finished startup roughly 50 seconds
later. That failed attempt does not establish a fully loaded client's pack
compatibility. The parent's subsequent candidate33 run verified one normal
connection after actual readiness, without the early NeoForge rejection. This
remains separate from the new diagnostic source and from gameplay acceptance.

Version 0.1.5 adds one explicitly requested `worldgen-export` per QA launch on the
private staging endpoint only. It requires the same owner, expiring nonce,
authenticated online player, normal ready game and unique request ID as the other
QA actions. A request may set `full_encodings: true`; this is opt-in private data.
The request invokes exactly public
`WorldgenFingerprintDiagnostics.writeLoadedClient(Path,String,boolean)` by typed
MethodHandle. It never enumerates class members, calls SeedGen's `get` or `load`,
changes registry data, or sends a gameplay/server command. The bridge must contain
the parent-reviewed diagnostic class and its exact diagnostic-only codec scope.
Candidate 35 includes both. A missing helper or unprepared cache fails explicitly
and is not retried.
JSONL/status files stay under the owned instance's `awft-qa/worldgen-inputs`;
the action receipt points to the status, which must be inspected even when dispatch
returns normally. Neither an export nor a matching diagnostic digest authorizes
SeedGen generation. The 0.1.5 helper compiled and its actual candidate 35 cached
client export completed with 1,950 entries and no encoding errors. The paired
native fingerprints still differ; see `docs/NATIVE-CANDIDATE35.md`.

Version **0.1.6** adds explicit native Xaero map actions on the authenticated
loopback staging endpoint `127.0.0.1:25575` only. The same listener handles them
after the existing ownership, expiry, nonce, unique-ID, account and server checks.
Ordinary pose, lighting, export and capture actions still reject open screens.
Map actions accept only the exact `GuiMap` instance this helper opened in the
same native Xaero session; they cannot capture or close another UI.

Each request still supplies its own unique `id`, current authorization `nonce`
and `action`. The map-specific fields are:

| Action | Fields | Result |
| --- | --- | --- |
| `map-open` | `dimension`, for example `minecraft:overworld` | Opens the author's real World Map screen; only existing session dimensions are accepted. |
| `map-view` | `center: [x,z]`, `zoom` | Changes this map's camera and invokes the native zoom limits/animation. It never moves the player. |
| `map-status` | None | Records actual dimension, center, user/target/render scale, UI size and MapHorizons/ShareFetch diagnostics. |
| `map-capture` | `expected_dimension`, `expected_center: [x,z]`, `expected_zoom` | Saves the actual framebuffer only after two separately rendered observations agree on the expected native view. |
| `map-close` | None | Restores this view's previous dimension selection, target zoom and camera-attachment preference, then closes only its own screen. |

Map captures share the existing **96 capture**, **8 megapixel** and storage
reserve limits. Two distinct `RenderFrameEvent.Post` observations must report the
requested native dimension, center within half a block, converged zoom within
0.1%, and mutually agreeing center/zoom. A one-second polling interval or elapsed
time never proves readiness. A request stops after 60 seconds without those
conditions. Changed expected values under the same ID fail; a different authorized
request cancels a pending capture with its own terminal receipt. Native map painting
can still be incomplete when view state is ready, so inspect the actual image.

Map receipts are private create-once JSON plus a SHA256 `.complete` seal. Failed
requests are terminal and are not automatically retried or logged every poll.
Existing images and receipts are preserved across launches. If the storage reserve
prevents even a small failure receipt, the request is marked complete in memory
and logs one error. An authorized normal disconnect or quit restores a currently
safe, exact owned map view first; a detached session or another UI is never changed.

The helper constructs the same native `GuiMap` as Xaero's normal open-map control.
The pinned 1.47.0 API lacks public center access, so narrowly named typed
MethodHandles/VarHandles read/write its camera fields and invoke native
`changeZoom`. No class-member enumeration, second listener, custom renderer,
discovery editing, seed lookup or generation call is added. Ordinary author
MapHorizons **ShareFetch may download permitted server LODs when the map opens**;
the receipt records whether it is enabled. Such downloads must be distinguished
from a genuine coarse-only adapter result. A saved SQL payload or matching camera
alone does not prove rendered terrain, exploration, permissions or SeedGen parity.

Build with Python 3.12+ and Java 21 using `python -B -m tools.build_settlement_qa`.
It requires the exact cached Xaero World Map 1.47.0 and MapHorizons 1.1.0-awft.2
compile-only APIs; `--maphorizons-api PATH` can select the exact reviewed artifact
before cache integration. Their sizes and SHA256 hashes, plus the author's nested
XaeroLib 1.7.3, are checked. None is packaged inside the QA JAR. The bounded build
also runs 23 pure rendered-readiness fixtures, without starting Minecraft or
initializing native GUI handles. **Actual transformed UI linkage, native map
rendering and a genuine coarse-only data view remain unverified.** QA 0.1.6 is
not installed by its build helper and remains excluded from release exports.

Capture requires an expiring authorization nonce, the expected account, server,
position and a uniquely named request. It permits at most 96 captures per launch,
with an 8-megapixel framebuffer bound,
checks free space before each and writes the actual camera position alongside the
image. An explicitly requested pose sends normal authenticated spectator and
teleport commands as the signed-in operator, confined to the surveyed area. The
server still enforces permission; this cannot move another player.
An authorized `quit` request follows Minecraft's normal shutdown path.

Screenshots obtained with this helper are real shader/game render evidence with
an additional QA mod installed. They do not prove a clean release import or an
unmodified-client acceptance test. Authorization files, screenshots and receipts
stay in the private owned instance and are never published automatically.
