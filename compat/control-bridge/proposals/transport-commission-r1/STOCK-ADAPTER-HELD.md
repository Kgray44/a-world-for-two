# Held stock-adapter checkpoint

## Execution correction: source requalified, runtime still held

At the owner's October28 execution correction, the unchanged final adapter was
recompiled against the actual candidate55/bridge0.6.41 API. Compilation passed
with zero diagnostics. The exact source SHA is
`eee5a7b9bec1e8c6a599616ec26b66a0d2210861525aa49f5d760616f2f9e3dc`;
compiled adapter class SHA is
`8732d306c6f533b1564371d84b6357238503a7e0a533a931a9ac02ba2f36dfed`.
The latest publisher/status/private-settings and unknown-partial guards are in
those compiled bytes. Actual Lease/Interlock signatures match ControlBridge.
The existing producer run passed13 tests with one symlink-permission skip; its
Windows junction case passed. Eight actual compiled parser-only cases passed.
The earlier wrong-checkout test invocation and prior failures remain preserved.
Qualification receipts are in `.local/stock-adapter-0.6.41-qualification-r1/`.

This removes the earlier source-compilation hold for this exact revision. There
has still been no native stock inspection/supply, H write, runtime installation
or gameplay acceptance. Master must review/integrate into a new immutable bridge
version and grant the exclusive execution lease before any request publication.

Minimal integration: include the adapter and the three existing callable rail
helpers in active sources; construct CopperWrenStockSupport with the next exact
candidate/bridge and `this::acquire`; register only its `commands` listener. It has
no tick/lifecycle hook. Add its exact inspect/supply packet command to the existing
private-owner/port gate and require confirmation for supply. Never republish55.
The producer writes only a new owned local source directory. Publish each exact
request with CREATE_NEW under the lease, then invoke its returned command once.
Requests expire after120seconds; supply needs its genuine same-JVM inspection
within60seconds. Existing fixed stock intents prohibit restock/replay/refund.

## Preserved historical hold

Master stopped optional adapter work at20:43UTC to prioritize the existing-command
zipline generation plan. These additional files are preserved source, **not
qualified for runtime integration or execution**:

- `CopperWrenStockSupport.java`
- `tools/transport_stock_request.py`
- `tests/test_transport_stock_request.py`

Producer fixtures:14tests run, one Windows symlink-permission skip; the Windows
junction case passed. Earlier Java compilation and eight parser-only cases passed.
The subsequent publisher-directory/status/private-settings and partial-mutation
evidence guards are unfinished or **not recompiled/qualified**. Final lifecycle,
allowlist instructions and independent review are unfinished. Do not infer
runtime acceptance from the earlier compile/parser receipts.

Original args/compiler/parser logs, including the first failed Windows-backslash
classpath harness, remain in `.local/rail-stock-adapter-compile-r1/`. No command,
world edit or native dashboard publication occurred during this work.

The previously committed three callable rail helpers and their documented manual
creative-client fallback are separate. Actual hardware stocking still requires
specific master authorization and genuine before/after custody. No new lease was
granted. This checkpoint authorizes no stock, generation, retry or deployment.
