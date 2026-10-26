# Build checkpoints

## 2026-10-26 — foundation and metadata

- Read the full build directive and cozy/weather/DH addendum. The latter supersedes
  Voxy/Roxy, Traveler's Backpack and default Fog/Better Fog. All other requested features remain in scope.
- Cloned the empty target repository into its dedicated source directory.
- Inspected the reference repository read-only at `594e00cd63b6abdcc199928576d8682932a0d959`.
- Guarded source work at <=100 MiB on C: and bounded runtime downloads/install steps on D:.
- Installed Java already present: Oracle Java 21.0.10, Python 3.12.10, psutil 7.2.2.
- Installed official NeoForge 21.1.255 from its SHA-256-pinned Maven installer on D:.
- Owner explicitly accepted Minecraft's EULA for this project and disposable test servers.
  The local acceptance receipt is kept outside Git.
- Verified KG and Sera's supplied Java profiles using Mojang and populated the local whitelist.
  Credentials were not requested or read.
- Resolved 101 pinned files, 474,833,373 download bytes. Verified every upstream file hash.
- Current static JAR check: 97 active mod JARs, zero dependency/duplicate/range errors;
  shaders and optional disabled Essential are handled separately. This is **not runtime acceptance**.

## Findings preserved during integration

- Stable Iris 1.8.12/Sodium 0.6.13 conflicts with current Sable/Veil. The candidate
  uses exact Iris 1.8.14-beta.1 and Sodium 0.8.13, explicitly treating Iris as a beta.
- Latest Let Me Despawn/Almanac requires NeoForge 21.1.262. Selected the compatible
  pre-1.26.10 release line instead of bypassing loader constraints.
- Take a Seat's JAR declares Player Animation Library on both sides. The library is
  included on both sides for dedicated startup validation.
- Minecraft 1.21 constraints on some client JARs are accepted by FancyModLoader's
  **own** 1.21.1 VersionSupportMatrix. The static validator reproduces that documented
  loader behavior; it does not edit downloaded JAR declarations.
- Advanced Weather advertises shader fog limitations. Its version-specific common
  and client configuration must be verified before enabling the final fog profile.

Remaining checkpoints: executable safety tests, dashboard browser QA, disposable
server/terrain startup, client/export/update tests, measured runtime evidence, real
two-player/graphics acceptance and production qualification.
