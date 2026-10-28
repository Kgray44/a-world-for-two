# Inventory and progress custody before the north rebuild

Rejecting a building's appearance does not discard the owner's items or later
play. `tools.artistic_north_rebuild_custody` audits all 52 rejected additions
(37 eastern, 15 western) against their exact original source, original saved
before plans and an explicitly verified stopped artistic checkpoint. It never
creates a demolition, rollback, restoration, relocation or inventory-copy plan.

The first audit covers 127,950 addressed source cells and 727 actual saved block
entities. The complete typed NBT is retained **privately**, including byte/int/
long widths, empty list subtype, item components and custom storage. These files
contain world/player/item data and must not be committed to Git. A real later bed
exists where the original recipe expected air; blanket restoration would remove
genuine progress.

Source-exact solids are recorded separately from source air, unspecified native
defaults and changed states. Neighbor-derived window/roof/fence/wall properties
are not silently ignored, and a state difference is not automatically called a
human edit. Accepted original structures and their addressed clearances keep
priority. Common streets and roof skirts are not assigned exclusive ownership
to the nearest house merely for convenience.

Every current BE stays protected. An absent `Items` key never proves a container
empty. Unopened loot tables, mod storage and item components stay explicit
unknowns until actual native inspection. Saved BE identifiers do not by
themselves prove the runtime class, `Container` interface, slot count or every
current `ItemStack` component. The audit reads no live region file and never
unpacks a loot table.

Before a small reviewed rebuild transaction, the parent must check fresh native
block/container state and all current slots/components. Prefer preserving an
anchor in place inside the redesigned interior. Any necessary move needs a real
lossless custody operation with before/debit/credit/readback evidence and no
duplication; copying saved inventory NBT is not that operation. A newer play
session invalidates an older snapshot's authority to overwrite current progress.

The private writer is bounded to two authenticated MCA members, 128 MiB raw,
256 MiB observed reader RSS, 180 seconds and 48 MiB output. ReserveGuard admits a
finite 64 MiB D: budget before it starts. Failed partial receipts remain. This is
saved evidence only; no demolition, native inventory transfer or owner artistic
acceptance is implied.
