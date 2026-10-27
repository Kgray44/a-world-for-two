# Shader choices

Only one shader renders at a time. All are client files; intended cost and appearance
describe author goals, not measured rankings. Author ZIPs are kept unchanged.

| Shader | Pin | Role | Distant Horizons evidence |
|---|---|---|---|
| BSL | 10.1.8 | Soft and warm | Archive inspected; full test pending |
| Complementary Reimagined | 5.9.3 | Cozy Minecraft-style candidate | Archive inspected; full test pending |
| Complementary Unbound | 5.9.3 | Realistic cinematic light | Enabled during owner playtest; full test pending |
| [Kappa](https://modrinth.com/shader/kappa-shader/version/8p4viq8V) | 5.3 | High-detail realistic/stylized | No DH terrain/water programs in this ZIP |
| [Bliss](https://modrinth.com/shader/bliss-shader/version/kC2Y8q1P) | 2.1.2 | Warm fantasy and changing skies | DH programs present; runtime pending |
| [Photon](https://modrinth.com/shader/photon-shader/version/BnGklH5y) | 1.4 | Scalable natural lighting | DH programs present; runtime pending |
| [MakeUp Ultra Fast](https://modrinth.com/shader/makeup-ultra-fast-shaders/version/t4YRxQug) | 9.6 | Lighter effects and color schemes | DH programs present; runtime pending |
| [Solas](https://modrinth.com/shader/solas-shader/version/XE9yh7pS) | 3.8 | Cozy fantasy, auroras and colored light | DH programs present; runtime pending |

These established projects have substantial public download counts. That indicates
popularity, not a universal quality ranking. Start with Medium/Low in MakeUp or
Complementary; test the more expensive Kappa effects with measured headroom.
Photon 1.4 adds Colorwheel support; this pack's complete Create rendering still needs testing.

The requested original [Chocapic13](https://www.curseforge.com/minecraft/shaders/chocapic13-shaders)
remains in the inventory. Its V9/V9.1 releases are legacy, automated retrieval returned
HTTP 403, and native Iris/DH compatibility is unverified. An unchanged author download
is needed. Bliss credits Chocapic but is not substituted for the original request.
Pastel 1.200 remains a cozy research candidate with version/DH questions unresolved.

DH program presence is a prerequisite, not runtime acceptance. Check distant terrain,
water transitions, three dimensions, storms, Create moving geometry, Sable ships,
translucent entities and long frames. Do not add OptiFine to the Iris/Sodium stack.

## Observed reload interruption

During the official two-player session on 2026-10-27 UTC, KG selected Complementary
Unbound r5.9.3 on HIGH. The log interval from destroying the old pipeline to the
next render/chunk-worker progress was 44.771 seconds; the server recorded a client
timeout during that pause. No fatal Iris compilation, out-of-memory or JVM-crash
marker was found in that interval. Sable's queued null-channel errors appeared
after its UDP channel closed. The game process survived and KG rejoined while
Sera remained connected.

KG subsequently selected Reimagined r5.9.3 on HIGH; its observed reload interval
was about 0.992 seconds. These are two log intervals on a memory-constrained shared
host, not controlled shader compilation benchmarks or proof of the underlying
cause. Shader switching and the remaining Iris uniform warnings still require
investigation. See [the session evidence](../evidence/runtime/two-player-session-candidate.23.json).
