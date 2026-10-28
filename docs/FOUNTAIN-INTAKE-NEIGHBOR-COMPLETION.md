# Ordinary intake neighbor completion proposal

The earlier one-cell plain-pool repair used PLACE with flags2|16. No normal settle
was recorded for that placement. An unnotified transport endpoint is a hypothesis,
not an established cause of the prior missing header flow.

This separate proposal observes only the existing e55 checkpoint pair:
`(1139,65,-1129)` source water0 and `(1139,66,-1129)` the full existing input-pipe
state. It emits a verification-only BEFORE2 and a pending normal-settle-only2
field, never a PLACE delta. A genuine fresh, complete native BEFORE2 with clean
resources is mandatory before the producer binds a settle-only output.

Current SettlementSupport skips BE targets, so the pipe BE is deliberately retained
and counted as one skipped target. The ordinary non-BE water target performs normal
shape/neighbor handling and updateNeighborsAt; that notifies its adjacent pipe BE
through native callbacks. No direct BE reinitialization, pressure/cache injection,
NBT load or claimed pipe-BE shape rewrite is introduced. Ordinary native callback
effects may occur; they are not an authored source/control replacement.

After the owner leaves, root verifies the pair and performs the admitted normal
settle, retaining its actual skip/change/cleanup result and unchanged-state check.
Together with the separately frozen two-runoff cleanup, this precedes a normal
stop, fresh dry checkpoint, complete2532 binding and newly pinned real fountain
commission. Header, wheel source, piston, controls and statue topology are outside
this proposal. The online preview, active helper/JAR and all earlier frozen sources
remain untouched; no pumped-function fix is claimed.
