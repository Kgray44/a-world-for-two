# Release process

Source can be published while a candidate is being tested. A stable playable release
must satisfy its exact acceptance gates; pending tests stay pending in the documentation.

1. Review all candidates and retain exclusions/unresolved decisions in the inventory.
2. Build owned compatibility components from pinned sources; preserve licenses and provenance.
3. Validate Python/JavaScript, exact JAR dependencies and the complete Packwiz hash chain.
4. Qualify the exact candidate: dedicated/client startup, relevant feature tests,
   backup/restore, graphics/worldgen and real remote two-player synchronization.
   For 0.2.0 only, the owner approved KG-only acceptance on
   manifest `17d52a3b408dcdff8ae46d53412f0f3427a86547e1af7a6a978e807237384b3c`.
   The owner directed release without a repeat KG join, using the completed
   copied-world play test. Record the dedicated KG join and two-player sync
   as unverified and retain the other acceptance checks.
5. Run `python -m tools.prism_export`. Verify portable `instance.cfg`, `mmc-pack.json`,
   pinned bootstrap/full-installer chain and project configuration. Exclude credentials,
   worlds, host Java paths and unauthorized third-party redistribution.
6. Stage a draft GitHub Release with ZIP, checksum, compatibility inventory, changelog
   and licensed compatibility artifacts. Draft does not mean acceptance passed.
7. Verify all public author downloads, resolving restrictions through authorized
   distribution. Test a fresh native Prism import before a one-download/import claim.
8. Publish an immutable tested tree at
   `https://kgray44.github.io/a-world-for-two/releases/<version>/pack.toml` and verify hashes.
9. Stop and back up production, then activate the verified immutable manifest.
   Once the matching server is ready, set `stable` in `catalog/publication.json`
   to that qualified version and dispatch the Pages workflow. Verify the root
   Packwiz hash matches production before telling players to relaunch. Keep
   the previous immutable snapshots available for rollback. A rollback must
   coordinate the server and the stable channel in the same way.
10. Publish the qualified release, update README/status, then retire obsolete disposable
    staging while retaining useful worlds, unique history and failed receipts.

Pages must deploy an approved generated tree. Do not publish each in-progress main
commit as a playable update. Source CI and release publication remain separate.
