# Shortest private deployment: two new JARs on both sides

Source only. The master remains the sole installer/world/client operator.
Everything below is prepared; no installation, restart or native command was
performed by this chat. All older adapter hashes are superseded by this package.

## Exact files

Private root `P = D:\A World for Two\staging\drowned-rose-source-20261029`.
Exact sources, targets, bytes and SHA256s are in
`P\deploy-c806ec\INSTALL-MANIFEST.json`.

| File | Target | Pin |
| --- | --- | --- |
| `P\easy_npc-neoforge-1.21.1-7.17.1.jar` | Existing server `mods` and matching existing client `.minecraft\mods` |3,038,455bytes; SHA256 `b9ff47febbc3d2d5f2b8785e94178174e8eeb9d24e4fcb7a1d33c3770af4d823`; Modrinth `QyvBBoEd` |
| `P\compile-deploy-c806ec\awft-tavern-0.1.0.jar` | Same two mod directories |52,437bytes; SHA256 `9722a2f7382a3dcb5a5b032e9b786d02321ba8596c00eff85a9318d73adfd03a` |
| `P\deploy-c806ec\awft-tavern.json` | Server `config` ONLY |SHA256 `b2963d58e4dd14e542c24e2b926ddb76ead1a3a7b627a951a2fb348ca85929a4` |

Server root is
`D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\server`.
The current owned-client receipt identifies
`D:\A World for Two\instances\AWFT_Check_20261026_214756\.minecraft`.
Master confirms that is the matching closed KG instance before copying.
Do not create another client/world, authenticate accounts, accept EULA, edit
inventories, replace a save, or remove another person's mod/config files.

The minimum is **Core + adapter**, not Core + Config UI + bundle. The built
adapter metadata was inspected: Config UI is actually **optional**, with exact
7.17.1 compatibility if present. No adapter Java code calls it. If UI editing is
later wanted, add matched `easy_npc_config_ui-neoforge-1.21.1-7.17.1.jar` on both
sides. Do not add the bundle. Existing Immersive Melodies0.8.0, Handcrafted4.0.3
and Resourceful Lib3.0.12 remain pinned.

## What requires restart

* Easy NPC adds entity registrations/renderers and networking, so initial Core
  installation requires a server restart and client relaunch. It cannot be
  introduced by `/reload` or server-only scripting.
* Scheduler, residency, path selection, speech and band coordination execute on
  the server. The adapter JAR also contains the30 skin assets; copying it to
  both sides is the simple supported deployment for this package.
* The tavern JSON is server-only. Install the prepared config before first
  start; it sets `spawn_admitted=true` but leaves `native_geometry_verified=false`.
  Startup does NOT create any residents. Explicit hash-bound initialization is
  still necessary. Inspect and initialize use the SAME cached config, so there
  is no second configuration edit/restart or fictional geometry flag.
* Music, per-resident enable/weight and scheduler suspend/resume are commands
  after installation and do not require restarts.

## Bounded master actions

1. Finish other native work and recheck actual player roster. Stop normally and
   take/verify a fresh checkpoint retaining the current269 managed residents and
   any completed pending batches. c806ec retains258 and is an authenticated
   historical source, not proof of the current269+ save.
2. For these file copies only, run ReserveGuard with C0 / D16,777,216. Total new
   copy bytes are6,450,487 across both sides plus config. Server/client launches
   retain their own separate bounded forecast and guards. Copy the two JARs and
   server JSON, verifying every hash and avoiding duplicate versions.
3. Root integrates the exact `awfttavern` console fullmatch patterns from
   `dashboard.py` under its existing artistic-runtime admission. The proposed
   UI itself can wait. Initialization accepts only a64-hex config hash, requires
   operator2, reads the whole native preimage and prepares all30 collision-free
   starts BEFORE inserting an entity. Existing cats/birds/players are not moved.
4. Restart the existing server, relaunch the same licensed client and join the
   custom tavern. Let the ordinary client load all four tavern chunks. The
   adapter never force-loads them. Stand in clear circulation away from starting
   positions; player presence within96blocks activates decisions and music.
5. Execute exactly:

```text
awfttavern inspect
awfttavern initialize b2963d58e4dd14e542c24e2b926ddb76ead1a3a7b627a951a2fb348ca85929a4
awfttavern status
```

`inspect` creates0 entities. Initialization creates at most30 and changes0
blocks. Any preflight refusal inserts none. A later insertion failure preserves
partial identities; checkpoint and inspect before a recovery, not blind retry.
Read the result and `H\dashboard\tavern\status.json`: require30 registered,
30 present, no fault and independently changing activities. Initial decisions
are spread over1–31seconds; four stage performers gather automatically.

6. Only after first return30 and matching status30, run the same initialize once
   more. It must return0 new, with exactly the same30 UUIDs. Preserve cat
   `97bcfbc6-75df-5d93-a12c-710c03205342`, bird
   `a322577e-d97c-400a-be53-4ff2b3efb1bd`, piano, stage, seats and inventories.
   c806ec scanned1,308 saved entity rows, found those two existing occupants,
   no HOME/JOB memory in the envelope and no proposed30 UUID/player collision.
   Actual native positions may differ; initialization checks current occupancy.
7. Observe real walking, sitting/standing/drinking, conversations and all four
   native instruments playing Monkey Island. Tune native tracks/volume after
   listening. Capture actual footage/screenshots and status; then normal save,
   restart and UUID reconciliation, chunk lifecycle and two-client checks.

Immediate bounded checkpoint:

```text
awfttavern suspend true
```

This stops the owned scheduler/routes/instruments and retains all entities and
residency. Root can resume with `awfttavern suspend false`. Music alone can be
toggled with `awfttavern music false|true`; no server restart or removal is needed.

## Pack pins and counters

`P\prepared-minimal-c806ec\packwiz\mods\easy-npc-core.pw.toml` is the exact
Core metadata pin. Its isolated dependency pack validates215 entries with the
baseline payload retained. The adapter is an explicit private staged artifact
with the hash above, not a fictional published download. Record that same hash
in both installed inventories; master reconciles candidate/version/Packwiz
publication after qualification. The current client prelaunch command is blank,
so this existing private instance does not fetch/remove files through Packwiz
on launch. Do not publish an untested pack to make a download URL exist.

The native LIFE ledger and tavern ledger are separate: current269 LIFE +30
tavern would be299 tracked across both scopes; all pending other32 would make
331 if actually introduced. LIFE's existing counter does not automatically
become299. Report both scopes and measure the actual combined workload.

The genuine remaining blocker is root's coordinated installation and real game
test, including client availability. No more mod research, extra world copy,
dashboard build, or native-geometry boolean is required to attempt this bounded
first deployment. Successful compilation is not gameplay acceptance.
