# Exact owner Create chain-conveyor delta

Source-only adapter for the explicit `kinetics.maxChainConveyorLength`32→128
change. Current128 is authoritative. ConnectibleChains maxChainRange96 is separate
and unchanged. This does not authorize a restart, client action, mechanism rebuild
or old7,941-cell replay; KG's zipline-done signal and a new lease are still needed.

Both the old producer and native controller compare current configuration hashes
against the frozen original systems manifest. This patch accepts just one exact
exception, while retaining the original manifest and every other genuine gate:

- Original Create config: `36216a05f3ed63106ba587c8c24ed6315385829e7f3dae695dcf545aba41a270`.
- Current Create config: `240471ba821bd0f5208ea11960d79aacdfeb25a40c6a689a2d6518d689d890ac`.
- Retained owner receipt: `2d1d800d95cbb249587fe8d00d8794a425da4e4f2952ccc74196cfe7936ecc20`.
- Exact evidence folder: `H/staging/owner-chain-conveyor128-1793230774200615600/`.

`tools.transport_owner_create_delta.binding` reads the full retained original,
current config and owner receipt without writing. It verifies both fixed hashes,
the exact single literal replacement and equal typed TOML values everywhere else.
The native patch pins those same original/current/evidence bytes; existing staged
hashing still verifies the CURRENT config, not the old file. The other two config
hashes, source/geometry checks, current-world proof, empty-world lease, real item
custody and durable no-replay contracts are unchanged. An unused delta refuses.

For a future normal source integration, include the new Python module and review
`source-approved-delta.patch`. `git apply --check` passed against both the owned
checkout and actual master source. The revised producer compiles in memory; six
focused tests passed. The actual16,890-byte retained original and16,891-byte
current config also passed the read-only adapter. No world/config file was changed.
The Java patch is **not compiled, installed or runtime-qualified**; use the master's
normal next build, never replace an immutable artifact. No extra config library,
controller, command, test instance or observation framework is introduced.

After explicit human handover, bind the current config in the next genuinely fresh
operation. This config-only exception does not make the historical mill recovery
safe against KG's changed blocks/connections/inventories or fix its rail defects.
Observe operation-relevant native behavior normally. File binding alone does not
prove that FML or an existing client has adopted128; the native report says so.
