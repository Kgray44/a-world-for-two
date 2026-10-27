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
compatibility. This source repair has not been installed or tested in a running
client; a normally authenticated connection after readiness remains separate
runtime evidence.

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
