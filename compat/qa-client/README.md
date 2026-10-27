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
