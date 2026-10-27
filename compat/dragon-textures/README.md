# Dedicated-client dragon texture investigation

**Proposal only. No world/entity change, JAR rewrite, asset alias, installation or renderer fix has been deployed.** The attraction sources remain frozen. The client was closed for this investigation; it is not a new graphical acceptance test.

## Finding

KG's retained client log records two failed texture loads each for `bdd:dragons/nightfury/male/null_male.png` and `bdd:dragons/terrible_terror/male/null_male.png`. The exact server and client BDD JARs are identical:

- `bdd-neoforge-1.21.1-1.3.0-alpha.jar`, SHA-256 `456cbab81fb3762cc2a981fa60eb545c22c9587602c8e4275b7d87e6f2f41e60`.
- BlueLib `2.4.3-neoforge-1.21.1-bluelib-2.4.3.jar`, SHA-256 `efcbc58b6f0f06062f4c8c937e049b21be3fab37f76285dd5078b6a927cc486b`.

Both `null_male.png` files are absent. Real skin textures and default `adult`/`child` variant definitions are present. This is not evidence that EMF, shaders, download corruption or absent species assets caused the failure.

The pinned BDD bytecode explains the invalid name. `BddBaseDragon.getDragonLocation()` queries BlueLib for the current variant's `adult` and `child` parameters, converts the results with `String.valueOf`, then builds a gendered path. An absent result becomes the literal string `null`. Its fallback recognizes blank stems, but not this nonblank sentinel. `BddDragonModel.getTextureResource` subsequently normalizes the native model's female paths to male paths; this investigation does not broaden into changing that native gender behavior.

The pinned library exposes a dedicated-client cache gap:

1. `ParameterUtils.getOptionalEntityCache` reads `ResourceCache.Server.getVariants()`.
2. That map initializes empty and is populated by the **server** variant reload lifecycle.
3. BlueLib's NeoForge login handler sends the controller cache, without an entity-variant parameter snapshot. Its `VariantsPacket` contains a `Set<String>` of names, not the `EntityCache` parameter data.
4. BDD's compiled classes contain no reference to that server variant cache or `EntityCache` for their own synchronization path.

A fresh remote client therefore has no demonstrated path to obtain the parameter map used by BDD's texture lookup. Missing lookup results plus the literal-null handling explain the observed paths. This is a source-backed dedicated-client synchronization defect, not a captured live cache dump. A malformed individual saved variant could independently cause a null lookup, so a future instrumented staging client must record cache presence, species and the existing synchronized variant name before changing behavior.

## Narrow repair proposal

Coordinate integration with the parent bridge/presentation owner first. Preserve every existing dragon's UUID, `Variant`, owner, name, age, gender, inventory, health, bond and position. Never reroll skins, repair entity NBT, remove/recreate dragons or install `null_male.png` aliases. A default texture alias would hide the cause and erase visible variant distinctions.

The robust repair is to mirror the **actual authoritative BDD variant parameters** to a client-only cache after server loading completes and on datapack reload. Use the native server `EntityCache`/`VariantCache` records or an explicitly bounded rendering snapshot of their actual resolved parameters. The library's existing controller-cache packet is the appropriate lifecycle pattern. Require an exact BDD/BlueLib pin and a bounded payload; send only BDD species/variants and metadata, never third-party image bytes or world/player data. Do not guess a client variant map: BlueLib 2.4.3's `ResourceCache.Client` contains model/animation caches only.

The renderer hook should act only on BDD's failed parameter lookup for the **existing synchronized variant** and use that authoritative snapshot for `adult`, `child`, `hasGender` and any texture-layer parameters the native model requires. Keep normal successful native lookups unchanged. Validate selected resource existence against the actual client resource manager and honor resource-pack overrides. Unknown variants or missing authoritative data must remain an explicit diagnostic; never silently substitute another skin.

Store the mirror separately from `ResourceCache.Server.VARIANTS` and use it only on the logical rendering client. Replacing that static server map on a physical client can affect an integrated server in the same JVM. Clear the mirror on disconnect, change its generation on reload, and avoid retaining another server's metadata. Apply the hook at the BDD model/texture boundary rather than globally changing BlueLib gameplay parameter lookups. The exact small adapter must be reviewed against BDD glow/saddle/tail layers before integration.

A local-only fallback that reads the installed JAR's `data/bdd/dragons/...` definitions could restore default-pack appearances, but it would ignore server datapack overrides. It is insufficient as the final multiplayer repair and is not implemented here.

Acceptance requires an actual staging dedicated server and fresh client: retain the same dragon identities, show multiple named variants of each affected species, verify adult/baby and native gender/layer behavior, reconnect and reload, confirm no `null_male.png` lookup and inspect with the intended shader profile. A successful static probe cannot prove this.

## Reproducible read-only probe

Run `probe.py` with `--server-jar`, `--client-jar`, `--bluelib-jar`, and optionally `--client-log`. It verifies the exact pins, checks original asset existence/PNG dimensions, emits class identities and a bounded cache-reference census, and counts the specific missing-path warnings. Output is sanitized JSON on stdout only. No extraction, region/entity NBT access, Java launch, asset copying or installation occurs. Its class constant-pool evidence is distinguished from the manually inspected method bytecode and live runtime state.

Read-only `javap -J-Xmx128m` method inspection additionally established the actual lookup, empty-cache initialization and login packet code paths. Only one such headless process ran at a time. No Minecraft client/server or native world command ran.

## Primary sources and license

- [Official pinned BDD release](https://modrinth.com/mod/bluedude-dragons/version/gKRLQn5o): NeoForge 1.21.1, version 1.3.0-alpha. The project metadata and installed `neoforge.mods.toml` both declare **All Rights Reserved**. No public source or issue tracker is linked in the official Modrinth API metadata; its listed support link is Discord. No author was contacted.
- [BlueLib 2.4.3 release](https://github.com/MeAlam1/BlueLib/releases/tag/2.4.3), exact source commit `2c1c373ea8ffc4aeec10234fc1a1ff2eaafd07ae`.
- [Parameter lookup](https://github.com/MeAlam1/BlueLib/blob/2c1c373ea8ffc4aeec10234fc1a1ff2eaafd07ae/common/src/main/java/software/bluelib/api/utils/variant/ParameterUtils.java), [resource caches](https://github.com/MeAlam1/BlueLib/blob/2c1c373ea8ffc4aeec10234fc1a1ff2eaafd07ae/common/src/main/java/software/bluelib/loader/cache/ResourceCache.java), [NeoForge login handler](https://github.com/MeAlam1/BlueLib/blob/2c1c373ea8ffc4aeec10234fc1a1ff2eaafd07ae/neoforge/src/main/java/software/bluelib/BlueLib.java), and [names-only packet](https://github.com/MeAlam1/BlueLib/blob/2c1c373ea8ffc4aeec10234fc1a1ff2eaafd07ae/common/src/main/java/software/bluelib/net/messages/client/variant/VariantsPacket.java).
- [BlueLib issue tracker](https://github.com/MeAlam1/BlueLib/issues): the latest 100 open/closed entries were inspected by API. Relevant historical variant-loader changes exist, including [PR 131](https://github.com/MeAlam1/BlueLib/pull/131); no exact matching confirmed fix was found in that bounded review. A historical PR description is not proof that the pinned packet synchronizes parameters.
- [BlueLib MIT license](https://github.com/MeAlam1/BlueLib/blob/2c1c373ea8ffc4aeec10234fc1a1ff2eaafd07ae/LICENSE). Any adapted library code must retain the required notice. This lane contains original analysis/probe code only, with no copied BDD textures, JSON definitions, bytecode or decompiled source. Linking to locally installed ARR content is not permission to redistribute it.

Source/probe work was guarded at C: 8 MiB, D: 0, preserving the separate 30 GiB reserves. That monitoring guard does not constrain unrelated applications or existing writers.
