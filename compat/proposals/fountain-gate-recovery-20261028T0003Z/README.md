# Native awake gate recovery, isolated candidate44 proposal

This replacement/patch is based on the exact active43 source SHA256
`aabeee216128e74e1bba9fe0e4bb7e6aa47881d61fcb71199c577cc95d1454e2`.
No active source, runtime or world was changed. Existing inspect, commission and
reset actions retain their behavior. Only the private console action
`awftfountain recover-gate <bundle> <request-sha>` is added.

The preserved checkpoint is20261027T232720Z-8d0bc0, SHA256
`9bc10263e655b70468d9aad2a4b6787c7d50068f68b7292ef91e60757d627de8`.
Its actual saved moving BE at OPEN_PLUG contains a north sticky piston head,
source=true, extending=true, progress0.0. The head remains a moving block while
the source base is extended, the port contains the quartz plug, the ordinary
lever is ON and the circuit is powered. Wheel source, header and all four jets
are dry. The intake pool source remains.

Private source evidence is under
`H/staging/fountain-gate-recovery-source-20261027T2359Z`:

- `gate-before.json`,14 exact actual saved block states, SHA256
  `67086be86d69902fdbf8e14cf4783d9b7c8a076df168e596effd399d1543958d`.
- `moving-before.json`, read-only decoded BE/source custody, SHA256
  `a60c57b8140243214045b29bf4899aec2bd88eb10408ba9a7417f26c44f3e834`.

The normal `awft-native-fountain:1` request retains exact private-world,
candidate/bridge/pack, current checkpoint and installed helper-class binding.
It adds three bounded hash/size/home-relative-path references:
`recover_gate_before`, `recover_gate_moving`, `recover_gate_native_verify`.
The last reference must be an actual fresh successful14-state native verification
receipt and authentic completion marker from this server's journal. Zero failures,
cleanup, temporary tickets and shared futures are required. No such proof or
request is manufactured by the proposal. The parent must add recover-gate to its
private typed controller allowlist when integrating this exact source.

The existing stage/port/empty-player/main-thread/shared maintenance interlock,
bounded FULL chunk loading and robust lifecycle cleanup remain. There is no
empty-timer reset during LOAD or the initial strict geometry read. Once the actual
MovingPiston BE has been read and verified, the helper requests ordinary STOPtrue
and wakes the world only inside the active gate phases. This preserves the chance
to inspect the frozen state before normal simulation changes it.

The real BE getters must report movedState piston_head facingnorth/typesticky/
shortfalse, directionnorth, isSourcePistontrue and extendingtrue. Actual progress
and last-tick values are recorded read-only. The helper never calls finalTick,
tick, loadAdditional, a BE setter or direct piston/plug/source update.

While awake, it holds the existing normal ON lever until the extended piston,
stationary head and quartz port remain settled for40ticks. It then uses the
ordinary OFF lever and attached support notifications, waiting for actual base
retraction, returned original quartz at OPEN_PLUG, AIR port, unpowered SOUTH
diode and no moving gate BE for40ticks. Both phases require actual wheel/pump0RPM,
all source/header/jet cells dry and retained intake water. Total action lifetime
is at most600server ticks; per-phase budgets are220/300ticks. Only normal lever
updates and their source-neighbor notifications are made.

Failure/cancellation retains the actual partial state and failure receipt. No
automatic replay or rollback occurs. Cleanup removes owned tickets and retains
the shared lease while outstanding futures still need cleanup. Success requires
a fresh stopped dry checkpoint before the separate R5 architecture producer;
it does not establish pumped commissioning, persistence, riding or artistic
acceptance.

Actual43 API compilation passed in the private evidence folder
`H/staging/fountain-gate-recovery-compile-20261028T0004Z`, receipt SHA256
`3aac185d65497da077d15aad1de3848973abf8ad4f7a21e02a7313858b28d7ee`.
No native call or player/entity simulation was performed by this proposal.
