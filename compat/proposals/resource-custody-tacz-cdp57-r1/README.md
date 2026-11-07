# Native TaCZ and CreateDragonsPlus server-data custody candidate

This isolated successor source is based on exact private bridge 0.6.56. It adds
two precise provider views and logs every opened pack ID/class before traversal.
Unknown implementations still refuse. Existing world/resource fingerprints,
effective override stacks, 60-second deadline and aggregate byte/count limits
remain mandatory. No pack is closed and no generated resource is substituted.

TaCZ 1.1.8-hotfix-r7's actual `GunPackLoader$1` overrides only the root icon. Its
parent's public `getChildren()` returns immutable ordered vanilla Path/File pack
children. Those children use the existing complete folder/ZIP custody. The real
parent supplies the first readable child's resource; every masked child is still
hashed before that selected native winner. Synthetic `PackMetadataSection` is
serialized by its native `MetadataSectionType.toJson`; it is not fabricated as a
raw `pack.mcmeta` file. Parent and child identities/order/metadata are rechecked.

CreateDragonsPlus 1.11.9's actual `RuntimePackResources` provides generated packs
for itself and Create Central Kitchen. The view pins the producer JAR/class,
requires the instance's real SERVER_DATA type, snapshots its actual Path-to-native
supplier map and checks it against public namespaces/list/get APIs. All raw map
members are hashed, including root files and invalid paths the native listing
rejects. The original listed and selected bytes must agree. Raw bytes are read
again through the same accumulator to detect mutation even when the supplier
identity stays unchanged. No native data generator is invoked by the view.
The native namespace algorithm also visits root icons/metadata relative to the
data directory. It can therefore declare literal `..`; Minecraft's namespace
character test accepts that spelling. The view preserves those declarations and
uses the original mod-file/path prefix behavior for every namespace, rather than
assuming only `data/<namespace>/...` keys participate. All raw bytes remain in
custody even where a native prefix exposes no logical resource.

The pinned archive inputs are the installed TaCZ and CreateDragonsPlus artifacts.
No additional dependencies or third-party classes are packaged. The standalone
fixture uses real provider methods with controlled native storage inputs; its
reflection/Unsafe setup exists only in the fixture, never in production code.
The fixture initializes vanilla's static registries for the genuine component
metadata codec. It starts no client, server, world or terrain generator. Its
initial missing-bootstrap failure and the first too-narrow namespace check are
retained in the private qualification history.

The finite static class-name audit found other candidate families, including
Create's separate `DynamicPack` and PuzzlesLib dynamic packs. That is not a live
selected-object inventory. Create's empty-root query has a double-slash prefix
quirk, so this native contract is deliberately not applied indiscriminately to
unknown providers. The next actual attempt logs all selected headers up front.

Compilation, fixture and native qualification status are recorded separately in
the private build receipt. Source presence alone is not strict parity, DH
generation/rendering, or a successful native handshake.
