# Rosewater garden arrival

`tools/artistic_castle_approach.py` prepares one private, bounded two-wide
walking route from the existing fixed bridge's western landing and south bank
stairs to the palace's actual south gate and lower rose court. The fixed span
already connects the eastern bridge arrival to that landing. A direct eastern
shore shortcut crosses water and is deliberately absent. The glazed northeast
wall is not presented as a doorway.

The new walk begins at `(1192, -1084)`, follows dry terrain around the north and
east of the palace, and reaches the existing gate at `(1213, -962)` and court at
`(1253, -994)`. Its maximum grade is one block, with native stone stair treads.
Four small groups combine a bench, side table, potted flower, lantern and real
four-line directional sign. Eight-block drain joints break long path runs.
The route does not introduce buildings or a broad plaza.

Preparation reads an authenticated stopped backup, the actual native registry,
and immutable castle/bridge/bascule exclusion plans. Every changed position has
an exact saved block-state preimage. Authored solids, authored room air and
native block entities are protected; existing reviewed outdoor paving is
adopted without mutation. The generator refuses water, retained objects,
terrain cuts, high retaining walls, blocked headroom and disconnected routes.
The whole authored outdoor delta passes the nine-block material-run limit.

The first private bundle contains **1,328 changes**, **757 path columns**, and
four sign block-entity tags, bound to stopped checkpoint
`20261027T093048Z-eafdca`. It contains no commands. Its immutable plan hash is
`2b458c72d1f0b67193bc70fbe8d91cd34a1fd0870938dbc7b35023b867562802`;
the exact `before.json` hash is
`15250081439cb77050b0d87828ecf56faa34793503838d20cc1d4b7211bd0cf8`.
Actual saved-state construction, connectivity, headroom, native palette and
payload/preimage identity checks passed. Native before comparison, placement,
walking and graphical review remain separate requirements; preparation alone
does not prove those outcomes.

The CLI requires a unique private staging destination and explicit exclusion
plans. A changed backup requires explicit new `--checkpoint-id` and
`--checkpoint-sha256` binding. Preparation writes only `prototype.json`,
`before.json` and `manifest.json`, with an eight-MiB bound; it does not contact
the game or edit a world. Run the host's reserve guard before invoking it.
