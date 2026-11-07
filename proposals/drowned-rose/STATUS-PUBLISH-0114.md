# 0.1.14: bounded Windows status-publication retry

Actual0.1.13 telemetry reported AccessDeniedException while atomically replacing
status.json.tmp with status.json. The asynchronous writer exposes any exception
as error; the next heartbeat latches that error into the scheduler's fault and
pause. A later successful status write clears the writer error but does not
clear the scheduler fault/pause. Fresh status with a retained earlier rename
fault therefore explains the inert tavern without an actor or world failure.

A private Java21 test reproduced this exact Windows denial by holding an
ordinary read handle without delete sharing. It used one writer and complete
old/new files; replacement succeeded after the reader closed. This does not
identify which process held the actual staging handle.

The repair retries only AccessDeniedException from the atomic move on the
existing single background writer. Six attempts use25/50/100/200/400ms backoff,
775ms total. No server tick sleeps, extra snapshot queue, non-atomic fallback,
partial target write or reader change is introduced. Interrupts are preserved.
Other errors fail immediately; an exhausted AccessDenied failure retains the
existing fatal error and pause handling. Storage-reserve, size, symlink and all
world/actor safety gates are unchanged.

This does not clear the currently running scheduler fault, unpause actors,
reinitialize a ledger or execute recovery. The coordinating chat owns any safe
matched restart. The actor identities, ledger and all behavior/rendering other
than status publication remain as in0.1.13. Actual heartbeat/activity recovery
must be checked in that subsequent runtime trial.
