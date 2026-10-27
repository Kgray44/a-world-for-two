# MapHorizons refresh candidate

Original MapHorizons code: Copyright (c) 2026 VolcanicMG, MIT.
Pinned author source: https://github.com/VolcanicMG/MapHorizons/tree/6c80ad5be5fff2c373388dfd6ff433667edd7217

The unchanged `DhSource.java.upstream` is the exact patch input. The author MIT
license is retained in `LICENSE.MapHorizons` and must accompany the derived JAR.
The original author source archive and this recipe are required source provenance.

A World for Two adds original multi-resolution coverage/projection and memoization
helpers, a read-only capped metadata refresh using DH's shaded JDBC driver,
an owned refresh lease with concurrent-update reconciliation, and provider-lifecycle
checks. The established MapHorizons renderer and server-provided visibility rules
remain in use. SeedGen is not modified or redistributed.
No custom terrain renderer or competing minimap is introduced.

Status: source-only candidate. Standalone helper/JDBC fixtures and pinned changed-class
compilation pass; no new mod JAR is packaged or installed. Runtime map painting,
unexplored-terrain fidelity, performance and graphics acceptance remain pending.
