# Retained bridge inspection cleanup R2

Additive from immutable public R1 `043581e94976791cb7b8c93089b54c47f96a530c1dbf76d717e1a80824a52c5d`.
The request schema, exact current two-glue custody checks and read-only operation
are unchanged. No geometry, glue, controls, programs or motion authority is added.

The existing server tick now retries unfinished resource cleanup on every tick,
without waking simulation. Completed shared futures are released, never cancelled.
Tickets must be released and every future complete before the shared lease closes.
A ticket or lease failure keeps ownership and is retried. The global busy guard
also remains held after the lease closes until a clean immutable terminal exists.

Immutable receipts precede the best-effort progress file. Pending and clean
phases each publish once, preventing a pending future from generating an immutable
file every tick. A failed immutable publication stays busy; explicit cancel/stop
retries publication. A progress-file failure cannot erase a clean terminal.

`BridgeCleanupProbe.java` exercises the same nested cleanup tail with real pending,
completed and exceptionally completed CompletableFutures, ticket/lease failure,
terminal publication failure, explicit retry, and progress publication failure.
It constructs no Level, entity, controller or world. Source/API fixture evidence
does not substitute for actual native bridge custody, cycles, restart or appearance.
