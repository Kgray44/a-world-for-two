# Small Ships remote config callback

Presentation `0.2.2` is a private build for a future candidate. Compilation and
all 16 actual-class config regression cases passed after both players logged out
and the client exited. It has **not been transformed, installed, or tested by
reconnecting a game client**. No Minecraft, server, or client was launched by
this validation, and the existing installed candidate is unchanged.

The observed client exception during `ModConfigEvent.Reloading` comes from Small
Ships calling `getFullPath()` for a synchronized SERVER config. Such a config has
real in-memory data and no local path. The server bridge's Unloading guard does
not execute on this client event.

The exact reviewed artifacts are Small Ships `2.0.2` (2,815,793 bytes, SHA-256
`aed11c65cd44a62309f52528727f83d05f74cced5cd93951692972273c340796`), its bundled
ForgeConfigApiPort `21.1.0` (105,212 bytes, SHA-256
`355bc608ced2a7007b0f6d8108230cb26f7fbd3b7a1cee7b0c4b56eccf57b85a`), and FML
`4.0.45` under NeoForge `21.1.262`. The downloaded third-party JARs are unchanged
and remain outside Git.

## Correction boundary

The client-only pseudo mixin targets only Small Ships' existing
`CommonModBus.initRegisterConfigs(ModConfigEvent)` callback. For `smallships`, it:

- Skips Unloading, after FML has already detached the spec.
- Skips Loading/Reloading only for a SERVER config with attached data whose
  `getFullPath()` throws the exact pinned non-file exception. Its originating
  stack frame must be `ModConfig.getFullPath`; unrelated errors are rethrown.
- Leaves every file-backed callback unchanged. An absent file that still has a
  path remains a disk-backed config and retains the original error/migration
  behavior. Detached Loading/Reloading, other config types, and other mod IDs
  do not enter the remote exception case.

FML sets the loaded data and calls `spec.acceptConfig` before posting the event.
The exact bundled Forge adapter forwards that data to `ForgeConfigSpec`, which
corrects values and resets cached getters. The correction therefore skips only
the later Small Ships disk-parse/migration attempt. It does not replace received
values, apply defaults instead, accept the data a second time, or fabricate a
file path. This conclusion is scoped to the reviewed adapter; FML's remote parser
itself contains a validation TODO.

Sources: [Small Ships callback at the reviewed commit](https://raw.githubusercontent.com/talhanation/smallships/4bfb8680a3fecd8c7e71506b941a79c51c49dffb/neoforge/src/main/java/com/talhanation/smallships/neoforge/common/CommonModBus.java),
[exact FML 4.0.45 source archive](https://maven.neoforged.net/releases/net/neoforged/fancymodloader/loader/4.0.45/loader-4.0.45-sources.jar),
and [upstream issue 58](https://github.com/talhanation/smallships/issues/58).
Issue 58 concerns Unloading; it does not establish that remote Reloading works.
The bundled adapter was inspected from its exact bytes; its current upstream
branch has subsequently changed and is not substituted for this pin.

## Actual-class regression and remaining gates

The probe under `probes/` uses the future built presentation JAR and actual pinned
FML, Small Ships, and bundled Forge adapter classes. A test-owned ModContainer,
real event bus, and delegating spec spy expose their results. Config parsing,
validation/correction, cache handling, and old-schema backup migration use the
original implementations. No simulated migration implementation is substituted.

Its 16 cases cover non-default remote values, a second payload after caching,
out-of-range and wrong-type corrections, pathless SERVER Loading, cache clearing
on Unloading, real file SERVER Loading/Reloading and exact old-schema backup
bytes, local CLIENT Loading/Reloading/Unloading, detached events, absent local files, config
type/mod boundaries, and unrelated or forged-message exceptions. The original
remote callback is also exercised as a failing negative control. The probe
checks the actual loaded class locations and binds all receipts to artifact and
source hashes. Any failure, partial result, or bounded log remains private.

While players occupy the memory-constrained host, this command only prints the
pending state and performs no Java launch or write:

```powershell
python -B compat/client-presentation/probes/run_smallships_config_probe.py
```

The CLI no-launch gate has separate Python tests that prohibit process creation
and writes while exercising its default and missing-artifact error paths:

```powershell
python -B -m unittest discover -s compat/client-presentation/probes -p test_runner_gate.py -v
```

These tests do not execute or qualify the 16 actual-class cases.

After a separately authorized resource window and a separate build from this
reviewed source, run with that exact new artifact:

```powershell
python -B compat/client-presentation/probes/run_smallships_config_probe.py `
  --home 'D:\A World for Two' `
  --presentation-jar 'D:\A World for Two\staging\OWNED-FUTURE-BUILD\awft-client-presentation-0.2.2.jar' `
  --execute-after-resource-window
```

The runner admits at most 16 MiB of new private D: files and 1 MiB on C: after a
live reserve check. Each Java/compiler child has a 128 MiB maximum heap, 96 MiB
metaspace cap, two active processors and below-normal priority. Child output is
limited to 1 MiB per phase. It does not fetch dependencies, run Forge/Minecraft,
or touch a real instance, save, config, server, tunnel, or client. An overdue
owned child is reported and not killed; no following Java phase is admitted.

The actual-class run passed all 16 cases with the exact 10,034-byte presentation
JAR, SHA-256 `754555b0fc47e923ff6aaeccb8d162b72d4a0056b4a04e85c06c3d5d4f06c765`.
Its private harness receipt has SHA-256
`679c546e42231b46f836299c10f3c7e3baa7db44834701859888d05ae2b6efed`.
Observed remote getters changed from 37 to 73 after caching; the real spec
corrected an out-of-range value to 0 and a wrong type to its default 30. The
original disk callback executed for both SERVER and CLIENT Loading/Reloading,
and the old-schema SERVER backup bytes matched exactly. The two Python CLI gate
tests also passed. These are headless config checks, not multiplayer acceptance.

The harness selects the exact dependency order declared in the installed pinned
`win_args.txt`, checks class provenance (including Guava 32.1.2), and does not load
installer-only Guava 20.0. Earlier failed compiler/classpath attempts, logs and
receipts were retained in separate private stages; none were relabelled as pass.

Mixin transformation/injection and native reconnect with the server's applied
values are separate pending checks. Candidate
24 integration, Packwiz, Prism exports, publication, and version transitions are
owned outside this component change; the existing candidate's bytes remain fixed.

## Separate hull texture proposal; not implemented

Fish of Thieves adds the valid boat wood `fishofthieves_coconut`, while the pinned
Small Ships JAR contains no `textures/entity/ship/fishofthieves_coconut.png`.
A proposed client-only fallback would intercept the `Boat.Type` texture overload
that populates `ShipRenderer.boatResources`, preserving a supplied coconut asset
when present and otherwise referencing an existing compatible hull texture such
as Small Ships' jungle texture. It would leave wood IDs, entity data, NBT, drops,
and server state unchanged. The entity texture getter alone does not cover the
actual render path, which reads that map directly. This palette fallback has
not been added to version 0.2.2; transformation, resource reload, and native
rendering would need separate validation before any later inclusion.
