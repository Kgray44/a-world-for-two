# Native settlement visual review

This small test helper is **excluded from Packwiz and release exports**. It can
save the real Minecraft framebuffer in an explicitly owned, signed-in test
instance connected normally to the loopback dedicated server. It neither renders
a substitute scene nor controls operating-system windows or game input.

Capture requires an expiring authorization nonce, the expected account, server,
position and a uniquely named request. It permits at most 32 captures per launch,
checks free space before each and writes the actual camera position alongside the
image. An explicitly requested pose sends normal authenticated spectator and
teleport commands as the signed-in operator, confined to the surveyed area. The
server still enforces permission; this cannot move another player.
An authorized `quit` request follows Minecraft's normal shutdown path.

Screenshots obtained with this helper are real shader/game render evidence with
an additional QA mod installed. They do not prove a clean release import or an
unmodified-client acceptance test. Authorization files, screenshots and receipts
stay in the private owned instance and are never published automatically.
