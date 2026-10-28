# Candidate 43 resource-custody proposal

This is a source-only replacement for `LithostitchedSeedgenResources.java`.
The proposal does not change registry values, native phase order, selected packs,
fingerprint codecs or comparisons, first-seed policy, queue/logout gates, or cache
publication. It has not been exercised by a transformed Minecraft loader.

## Observed failure

The actual candidate 42 client completed its first modded registry load, then
failed before the Lithostitched startup callback could apply its phases. The
native PathPackResources reader rejected the original metadata name
`cristellib:structure_config/t_and_t_ED.json` because its final path segment
contains uppercase letters. The attestor treated this native null lookup as a
missing enumerated resource and refused initialization. The later fallback
damage-type registry failure is separate and is not repaired or suppressed here.

The unchanged upstream archive is `t_and_t-fabric-neoforge-1.13.11.jar`,
3,553,006 bytes, SHA-256
`270fc0d1c99e54bc15f43d64bdaac60a90cb896efc357af624988e677136440f`.
Its exact member `data/cristellib/structure_config/t_and_t_ED.json` is 1,376 bytes,
SHA-256 `48a4d810f76523fbfecc68d616b3aa83ce8637ee58dec7ccb46771bddfc45ae9`.
No upstream bytes were copied into this proposal, renamed, or changed.

## Replacement and invariant

Replace only the active helper with
`compat/control-bridge/proposals/resource-custody43/LithostitchedSeedgenResources.java`.
The reviewed base helper hash is
`a8fa2fc7b6fc108bdb548031801762801b292825840479dcddd7dda703d83fcc`;
the replacement hash is
`d2e4649cf128c5573f7e5e48c2a4d5050ef80276a566ac0565a89ecd1178bc27`.
The class/package, callback signature, attestation record and external call sites
remain unchanged. No additional mixin registration is needed.

Attestation protocol 3 keeps three distinct, ordered kinds of evidence:

1. Every raw member's exact name, native path-parser result/error and unchanged
   bytes are hashed from the already admitted exact root or ZIP entry.
2. Each selected native resource records the parser result and actual supplier
   presence separately. A Path/Vanilla/File null is permitted only for a
   parser-rejected path whose exact raw member was already authenticated.
3. The actual resource manager's opened-pack identities, order and effective
   resource stacks, including a genuinely empty stack, remain independently
   hashed through native `getResourceStack`. Exceptions still refuse the load.

No raw member becomes a fabricated effective resource. A ZIP can serve an exact
uppercase name even when the path grammar rejects it; its readable native source
is retained. A Composite null is permitted only if each child selecting that ID
has an explicit unreadable witness. Any readable child, missing child proof or
valid-path disappearance refuses. Unknown pack implementations still refuse.

Native overlay/root order is preserved. Exact raw Path names are sorted within
each ordered root, because directory traversal order is not overlay precedence.
ZIP members retain their original central-directory order; duplicate raw member
names refuse rather than selecting ambiguous bytes. No content is normalized,
lowercased, filtered out or recovered through an arbitrary fallback path.

Bounds stay unchanged: 512 pack nodes, 262,144 attested entries, 1,048,576 tree
visits, 32 MiB per resource, 512 MiB total resource reads, 4,096-character identity
strings, depth 128 for a root and 16 for Composite recursion, and a cooperative
60-second deadline. Reads/close failures and incomplete native inventories still
refuse. No new game runtime, world, account, pack or installer is launched here.

## Actual-API fixture result and limits

Run from the project root with the existing installed libraries:

```text
python -B -m compat.seedgen.probe_resource_custody43 --home <owned-artistic-stage>
```

The focused Java source and replacement helper compiled against the actual
installed Minecraft 1.21.1 / NeoForge 21.1.262 APIs with a 256 MiB heap. All 27
checks passed: native Path null, native ZIP-readable original bytes, Composite
child preservation, absent/missing proof refusal, valid-path disappearance,
unchanged inventory determinism, raw invalid member mutation, masked child
mutation, actual pack order, bad data root and unknown subclass refusal.

The named, untransformed ResourceLocation factory rejects this uppercase name.
The test therefore uses its exact private constructor **only inside the fixture**
to represent the spelling already observed in the real NeoForge log. Production
does not construct invalid IDs or alter any ResourceLocation implementation.
The untransformed effective manager then rejects that synthetic ID when forming
its `.mcmeta` location. This limitation is asserted explicitly; it is not evidence
that the transformed manager returns an empty or nonempty stack. The complete
attestation tests use the real named API's own enumeration, while still hashing
every original raw invalid member.

Three earlier fixture failures are retained: an invalid compound `var`
declaration, an initially incomplete compile classpath, and the false offline
effective-stack expectation exposed above. The final proof is source- and
API-hash-bound; prior failures were not overwritten or reported as passes.

## Native integration gate

The parent must review and copy the replacement, build a new immutable candidate,
and perform one actual modded registry load plus authenticated fresh load. Both
must attest the same opened content and finish the original native phases before
any fresh cache publication. The actual transformed uppercase-ID/effective-stack
behavior remains a mandatory native gate; an unexpected error still refuses.
Only then can paired original fingerprint and effective semantic witnesses, full
packet acceptance, current-cache publication and actual LOD generation be tested.
This proposal proves none of those native acceptance outcomes.
