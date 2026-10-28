# Active preview alias

`python -B -m control_room.redirect --port 8765` is an optional local navigation
alias to the already running private preview at `http://127.0.0.1:8766`.
First verify that the obsolete 8765 dashboard has no active game or jobs, then
retire its owned dashboard process while preserving its history and ownership evidence. This helper never stops or starts either Control Room or game.

The helper binds only 127.0.0.1. GET and HEAD receive a 307 temporary redirect with
the original path and query. Browsers preserve an existing fragment such as
`#atlas` when the redirect's Location has no fragment; fragments are not sent in
HTTP requests. The destination is fixed to the preview's loopback origin. Incoming
Host must be exactly localhost or127.0.0.1 with the actual listening port. Absolute
targets, authority forms, userinfo origins, backslashes, invalid encoding and
control-character targets are rejected. Responses have no body and are no-store.

POST, PUT and other action methods receive 405 and are never forwarded. The helper
does not proxy APIs, rewrite Origin, copy tokens, add CORS permissions or manage
game processes. Refresh the browser page so the preview supplies its own current
session. Old tabs' action requests fail closed rather than being replayed against
another world. This is explicitly an **active preview alias**: the official world
has not moved and its previous failures/history have not been erased.

There is no timed shutdown. Ctrl+C follows the normal listener-close path. Request
paths and query strings are not logged; the CLI emits one bounded startup line or
a generic bind failure. The process owner may capture that output in a small owned
log. Source tests use only an owned ephemeral loopback listener and prove redirects,
method refusal, Host/target checks and listener cleanup. They do not deploy the
alias or establish browser, preview/game, authentication or artistic acceptance.

The owned preview alias was deployed on 2026-10-28. Actual local checks returned
307 for GET and 405 for POST while the active game process continued unchanged.
This is a dated deployment observation, not a permanent official-world handoff.
