# Dedicated-client dragon rendering repair

The pinned BDD/BlueLib combination could construct texture names such as
`null_male.png` on a dedicated client because the renderer could not obtain its
existing dragon variant's texture parameters. The repair supplies authoritative
rendering metadata to an isolated client cache. It does not change dragons,
replace variants, or add texture aliases.

## Cause and scope

The inspected pins are BDD `1.3.0-alpha` for NeoForge 1.21.1, SHA-256
`456cbab81fb3762cc2a981fa60eb545c22c9587602c8e4275b7d87e6f2f41e60`,
and BlueLib `2.4.3`, SHA-256
`efcbc58b6f0f06062f4c8c937e049b21be3fab37f76285dd5078b6a927cc486b`.
BDD's native texture lookup reads BlueLib variant parameters; a missing value
becomes the literal string `null`. The native blank-name fallback does not catch
that string. The relevant real textures exist in the unchanged BDD JAR.

BlueLib's server reload populates the parameter cache asynchronously. Its
dedicated-client login path does not provide the complete entity-variant
parameter map needed by that lookup: the variants packet carries names, while
the controller cache is a different data set. A lookup failure for an unknown
saved variant can also occur independently; the repair does not conceal it.

The [original diagnosis](../compat/dragon-textures/README.md) preserves the
read-only investigation and exact primary-source references. Its proposal-only
status describes that earlier investigation; the implementation and evidence
below supersede that status.

## Implemented behavior

The bridge observes the actual BlueLib reload future's completion and publishes
only BDD species, existing variant names, and the native resolved `adult`,
`child`, `hasGender`, and `glowing` scalar parameters. It uses BlueLib's native
metadata codec, with a 512 KiB wire limit, 64-species limit and 512-variant limit.
Completed snapshots are also delivered to a later joining negotiated client.

The optional client payload populates a separate rendering cache. It never
replaces BlueLib's server cache, including in an integrated-server JVM. Hooks
preserve successful native parameter lookups and consult the mirror only for
missing parameters of the existing synchronized variant. Unknown variants stay
explicitly missing. The glow lookup is covered separately; native saddle and
tail resource selection remains intact.

Connection identity guards reject old deliveries. Disconnect clears the
mirror; resource reload invalidates resource witnesses. The actual client
resource manager records whether a selected texture exists and which resource
pack supplies it, preserving overrides. No BDD image, definition, bytecode or
decompiled source is redistributed by this original adapter.

## Evidence and remaining acceptance

- The headless fixture passed the exact pinned BlueLib metadata codec and
  Minecraft wire-buffer round trip, isolated deep-copy checks, invalid-input
  rejection, preservation of successful native lookups, and missing-variant
  behavior. This is native-library fixture evidence, not graphical acceptance.
- During the actual candidate.25 dedicated-client login on 2026-10-27, the client
  accepted generation 2 with **7 species and 75 variants**, metadata SHA-256
  `45d3fa3d8a1d01b1aba945ea7c9bc45f3374291267a6d17ea6df3c9c5081f297`.
  Its snapshot witness recorded an isolated cache, zero entity/variant writes
  and zero texture aliases. The server independently published the same counts.
- Actual candidate.26 staging views and client resource-manager witnesses then
  confirmed distinct **black, nebula and leucistic Night Fury base textures**.
  The metadata cache remained isolated, with zero texture aliases and zero
  entity/variant writes. The [black Night Fury screenshot](images/artistic-recovery/nightfury-render.png)
  is a real game capture; it is not a replacement skin or extracted texture.
- Current immutable bridge **0.6.14** compiled at 180,206 bytes, SHA-256
  `6d3fb29b85d0ddd5f478674b9b4fc3f5aa150dc87d949ffc73bb20898667ee09`.
  It retains the same dragon sources; its subsequent changes concern native
  harbor inspection. Its dedicated-only classpath fixture reproduced the old
  harbor reflection failure and passed the direct-member getter with the
  client-only `CameraType` absent. That fixture supplies no dragon visual proof.

The optional glow-layer witness still reports a missing original upstream mask.
The adapter does not manufacture or alias that asset; **glow remains a separate
unresolved layer limit**. Successful base textures do not establish every
species, baby/gender combination, saddle/tail layer, shader, or datapack/resource
reload behavior. Those broader checks remain pending, along with multiplayer
gameplay acceptance. Reconnect/resource reload invalidate old diagnostic state;
a zero-generation file between connections is not a rendering failure. Preserve
the existing dragon identities and native variants throughout further checks;
replacement or skin reroll is not part of this repair.
