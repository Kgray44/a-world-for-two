# Retained bridge radio lifecycle repair — source proposal

This proposal is uninstalled. Active candidate47 Java, Control Room, versions,
JARs and the world remain unchanged. It does not qualify a repaired bridge.

The actual47 failed commissioning receipt `bf725b0e-2e57-40af-8956-a615953dbc42`
recorded a real15-strength transmitter pulse and closed, disassembled bearings.
Both receivers were alive/listening but absent from the native network, which
contained only the two retained transmitters. The native55° programs and2/8RPM
power were present. The failure and its cleanup receipt must remain intact.

The installed Create6.0.10 manifest identifies commit
`ac0c444d9828da3453ae8cc65338e8de063286fb`. Its
[LinkBehaviour lifecycle](https://github.com/Creators-of-Create/Create/blob/ac0c444d9828da3453ae8cc65338e8de063286fb/src/main/java/com/simibubi/create/content/redstone/link/LinkBehaviour.java)
adds the existing object in `initialize()` and removes it in `unload()`. It has no
tick/lazyTick override that periodically repairs missing membership.
`newPosition=true` is normal after initialization; it is not proof of a missing
tick. The
[network handler](https://github.com/Creators-of-Create/Create/blob/ac0c444d9828da3453ae8cc65338e8de063286fb/src/main/java/com/simibubi/create/content/redstone/link/RedstoneLinkNetworkHandler.java)
prunes actors that temporarily report not alive, while an ordinary signal update
does not re-add an alive missing receiver. This supports a registration-lifecycle
hypothesis. It does not establish exactly when these two receivers disappeared.
The installed binary methods were independently inspected with bounded Java21
`javap` after host RAM recovered.

`EngineeringSupport.java` adds a separate `repair-radio` action. Existing
simulation tickets, empty-server interlock, concrete native readiness and ticket
cleanup remain in use. Repair is limited to900 ticks, with at most600 for native
readiness and200 for the post-registration hold. It cannot enter setup or a pulse
branch, and `pulse()` independently rejects repair mode. No input is sent after
repair; a later, separately admitted commissioning action must perform the real
two cycles. Commissioning also gains40-tick radio readiness and an immediate
membership check before each input, without automatic initialization.

The repair checks the exact private stage, current owner/checkpoint, real
versioned release manifest, active/installed pack, actual helper version and three
actual class hashes. Its original marked native full verification must contain
all20,703 bridge targets, no failures or pending cleanup and be less than300
seconds old. It refuses unresolved quarantine. No flat Packwiz file is invented.

`NativeRadioLifecycle` retains the four exact BE objects, their registered link
objects, complete NBT, states, plain frequency items and native channel identity.
Only the two known transmitters may initially be members; no foreign member or
missing transmitter is accepted. All four actual chunks must already be FULL
and ticking. Both55° instruction lists are checked in full with their native
types, directions, modifiers and values. The mechanism must remain closed,
disassembled, idle and powered normally at2RPM/8RPM. Native `withinRange` must
reach both receivers from either control transmitter.

Only a missing retained receiver receives one normal `LinkBehaviour.initialize()`
call. There is no unload, frequency assignment, received-strength assignment,
kinetic setter, BE/NBT load, glue action, entity creation or fake player. Complete
radio NBT, identities and zero idle power are checked afterward. All four native
members must remain present for40 consecutive actual game ticks. A failure
retains initializer-attempt positions in the terminal report, and no automatic
retry or rollback is performed.

The Control Room patch admits only the exact confirmed private-stage command:
`awftengine repair-radio <engineering-plan-sha256>`. Wrong owners, permanent
worlds, ports, malformed hashes, extra arguments and command injection refuse.
The four focused tests execute the proposed real dispatcher method. The pure
Java probe covers15 readiness/recovery branch assertions. Both the complete
proposal and the probe compiled against the actual47 helper and its pinned
Minecraft/NeoForge/Create API classpath; no native game calls were executed.
The first compiler attempt failed only because Windows backslashes were not
valid Java argument-file paths; that failed receipt remains preserved. The
corrected and final compile/probe receipts are separate.

For the future engineering plan, add `radio_repair_custody` with these **actual
post-build** fields; do not reuse API-probe class hashes as runtime proof:

| Field | Required value |
| --- | --- |
| `format` | `awft-native-retained-radio-repair:1` |
| `candidate_version`, `bridge_version`, `pack_sha256` | Actual next installed candidate/helper/manifest |
| `engineering_class_sha256` | Actual built `EngineeringSupport.class` |
| `lifecycle_class_sha256` | Actual built `NativeRadioLifecycle.class` |
| `facts_class_sha256` | Actual built `RadioLifecycleFacts.class` |
| `native_full_verification` | Owned original native receipt reference with `path`, `bytes`, `sha256`; original `.complete` marker required |

After review, the parent may copy the three production Java files, apply the
Control Room patch, build and inspect its actual class identities. The probe is
a test source and need not be included in the production helper. No build,
installation, controller command or native repair was performed by this task.
