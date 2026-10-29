# Existing cog and tender controls: pinned-code handoff

Prepared 2026-10-28 from read-only cached bytecode, the existing KG client options file, and authenticated saved custody report `585920e187a5fc26cf2ff67e9da4a1db9b501ec6a837f759b14c6762b02e17ef`. These are practical instructions for the master's reserved native operator window. No controls were operated, no configuration was changed, and no sailing, boarding, collision, multiplayer or restart acceptance is claimed.

## Preserve the existing craft

The report binds to checkpoint `20261028T191243Z-6ad3a8`, archive SHA-256 `0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2`. It found each original craft exactly once:

| Craft | Original UUID | Saved position |
| --- | --- | --- |
| Small Ships cog | `62cd3578-b01b-5ab4-b7e8-6f74734cb4f4` | `(1196.5, 62.07772726508138, -1264.5)` |
| Vanilla boat tender | `59f253a3-00b6-576b-ae62-306aa75d8a8c` | `(1194.5, 62.52334561064546, -1253.5)` |

The saved cog has `ContainerSize=108`, main `Items=[]`, `HullDamage=0`, `locked=0`, `Sinking=0`, `Sunken=0`, and white sail state `0` / health `100`. Its actual passengers are `envelope:pigeon` in `Seat7` and `naturalist:butterfly` in `Seat3`. Saved `Seat0` is absent. Preserve both animals, their UUIDs, seat assignments, and all cargo/equipment data. These are saved facts; the master must re-establish current native identity, condition, passengers and inventory before interaction. Do not create a replacement craft or reset identity/custody to get controls working.

## Persisted KG bindings and their code behavior

The existing instance is `D:\A World for Two\instances\AWFT_Check_20261026_214756\.minecraft`. Its `options.txt` SHA-256 was `6ecd61509f712dc5796c6a73b4dc8c05576dad7d8381d660b24b034eb39737ad`, last modified `2026-10-28T04:54:21.417328+00:00`. These are persisted bindings, not a live UI observation; confirm the actual operator uses this instance and these bindings.

| Input | Cog | Existing vanilla boat tender |
| --- | --- | --- |
| Right mouse, empty hand, without Shift | Board an available seat. Avoid fitted cannon seating hit areas when seeking the helm. | Board if a seat is available. |
| W / S | Manoeuvre forward / reverse when allowed. With sail already set, also raise / lower its setting after the sail cooldown. | Row forward / reverse. |
| A / D | Steer left / right. | Turn left / right. |
| R | Driver only: toggle furled `0` to minimum set `1`; any set state returns to `0`. Leashing blocks this toggle. | No Small Ships sail control. |
| E while mounted | Open the cog cargo menu through `HasCustomInventoryScreen`. | Open player inventory; this `minecraft:boat` has no cargo container. |
| Left Shift + right mouse while outside | Open cargo instead of boarding, while unlocked. | Secondary use prevents ordinary boarding; no cargo menu. |
| Left Shift while mounted | Dismount. Stop and establish a safe exit first. | Dismount. Stop beside the verified landing first. |
| Space | **Cannon-fire input in driver/gunner seats. Do not use as throttle or a boarding/jump test.** | No sail/speed control is established by this audit. |

The file also binds Left Control to vanilla sprint and F to Small Ships cannon-barrel entry. This audit found no cog sprint throttle. F is handled for a ground cannon; it is not a helm or sail shortcut. Active Small Ships custom key registration contains only sail toggle and cannon-barrel entry. Older higher/lower-sail and ship-inventory language strings do not establish additional active key bindings.

## Confirming the real human helm

`CogEntity` defines eleven seats; ID `0` has `SeatType.DRIVER`, local `(v=-3, y=1.6, h=0)`. `Ship.getDriverAnySide()` searches DRIVER seats, resolves the UUID assignment against the actual passenger list, and requires a `Player`. It does not choose the first passenger for a seatable cog. The two animals therefore do not establish a human driver.

Board with an empty hand, without Shift, aiming at the hull/helm away from fitted cannon positions. `Ship.addPassenger()` first honors an eligible cannon/gunner hit; otherwise `findSeatAt(..., canDrive)` prefers a free DRIVER seat for an eligible player. Clicking a cannon position can select a gunner seat instead.

Before R or movement, the master must read the actual native seat assignments and mounted relationship: `SeatAssignments.Seat0` must resolve to the operator's real player UUID and that player must be a current passenger of this exact cog. Verify `Seat3` and `Seat7` still map to the same existing animals. A camera position or total passenger count does not prove the helm. If the operator occupies another seat, stop; use normal dismount/reboard away from cannon seating, preserving all other occupants. Do not edit seat NBT, eject animals or use cannon fire as a seat test.

## Bounded first use in the master-owned window

1. Reconfirm the current native craft census, operator bindings, clear short route, water/collision envelope and return landing. Record the existing cargo and passenger state. If the boat cannot embark, record the actual refusal; do not respawn it.
2. For the cog, confirm human `Seat0`. Start with sail state `0`. Only within the approved movement area, use brief W/S and A/D inputs to establish manoeuvring. R sets sail to `1`; W can then increase the sail state toward `4`, and S can reduce it only to `1`. Both changes are cooldown-gated. Do not assume a fixed delay from this audit or use held W in a confined berth.
3. R furls the sail to `0`. Releasing W/S leaves an already-set sail set; S is not an instant stop/furl command. Observe actual motion and clearance before dismounting. Code includes wind, damage and load modifiers; no measured speed, stopping distance or guaranteed reverse authority is available here.
4. At rest, E should open the cog cargo screen; outside, Shift + right click is the alternative. First prove opening/closing without moving stock. The saved empty main inventory is not permission to alter equipment slots or current contents. Any later transfer needs an exact item count before/after.
5. For the tender, ordinary right click boards; W/S rows and A/D turns. Test one short out-and-return path, then Left Shift beside the landing and verify actual safe exit/re-entry. The cog's R/E cargo behavior does not apply to this ordinary boat. Do not infer transfer, ladder reach or two-person clearance from these controls alone.

Capture the actual mounted seat, sail state and response, cargo screen, stop, dismount location, and preserved wildlife/craft identities. Two-player use, collision, restart persistence and performance remain separate native acceptance work under the master's scheduling authority. This document grants no placement, entity creation, inventory write or client-input authority.

## Exact local evidence

- Cached Small Ships `smallships-neoforge-1.21.1-2.0.2.jar` at `D:\A World for Two\caches\mods\`: SHA-256 `aed11c65cd44a62309f52528727f83d05f74cced5cd93951692972273c340796`; SHA-512 `3ca7ec4a9f6800a5e9f90cb273e8495c5919c2d9a0707160a1d4391fa11c5525e3f76038f877023929d3e3104b3df79e8afc1138de0f7df64530649cb3b76d20`. The sole Small Ships JAR in the named instance has that same SHA-512. This does not prove the currently running client/server loaded it.
- Read with JDK 21 `javap -c -p`: `client.option.ModGameOptions`, `KeyEvent`; `world.entity.ship.Ship` (`controlShip`, `interactAt`, `addPassenger`, `getDriverAnySide`, `getControllingPassenger`, `getDismountLocationForPassenger`); `ContainerShip` (`interact`, `openCustomInventoryScreen`); `CogEntity` seat definitions; `abilities.Sailable` (`toggleSail`, `controlBoatSailShip`); `abilities.Seatable` seat selection/assignment; `seat.ShipSeat` position transform. The cog dismount path can furl a set sail when its driver exits and searches near the seat, with fallback; a safe dock exit remains unproved.
- Cached Minecraft `client-1.21.1-20240808.144430-srg.jar`, SHA-256 `a649bd3ce77f122d0f83ae1b37b4b303e662470f928b9bee5fbc76580805ffd4`: `Minecraft` inventory-key dispatch, `MultiPlayerGameMode.isServerControlledInventory`, `LocalPlayer.sendOpenInventory`, `Boat.interact`, `Boat.controlBoat`, and native dismount handling establish the inventory/boat paths above. Bytecode inspection did not execute mod/game classes.
- Saved report and typed tags: `D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\staging\fleet-custody-585920e187a5fc26\`; cog typed-tag SHA-256 `dd697bd3dc6f8947b5537b4597020cadb921b4cbca20c2da86a9e933612bbd34`, tender typed-tag SHA-256 `407dcf7cb73e9607eb07701e915d9d2b22bef5e4fe616d8b3e04cc7d52bcc1b7`.

Only this document was written. Guard before the write: `2026-10-28T20:08:34.8852954Z`, estimate C `4,194,304` / D `0` bytes, allowed; free C `122,071,650,304` / D `283,521,462,272` bytes. The monitoring instruction does not constrain external applications or already-running writers. No runtime or repeat source test suite was run.
