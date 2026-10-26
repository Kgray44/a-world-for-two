# A World for Two

A cozy Minecraft 1.21.1 NeoForge world for KG and Sera, maintained with Packwiz,
Prism and a local Windows **Control Room**.

**Development candidate.** The implementation and acceptance work are in progress.
Pinned metadata and static dependency checks are not gameplay, graphics or multiplayer acceptance.
Do not promote a candidate into a permanent world or publish it as a verified release.

## Where things live

- `packwiz/`: canonical, hash-verified Packwiz release definition.
- `catalog/`: requested inventory, reviewed selections, generated exact release lock and schemas.
- `control_room/`: Python backend and buildless HTML/CSS/JavaScript dashboard.
- `tools/`: pack resolution, exports, compatibility and acceptance tooling.
- `evidence/`: actual verification receipts; private/raw caches are ignored.
- `docs/`: installation, compatibility, recovery and acceptance documentation.
- `windows/`: double-click Windows entry points.

Runtime data belongs in **`D:\A World for Two`**, separate from this source checkout.
Worlds, downloaded third-party JARs, accounts, tokens, logs and runtime caches stay out of Git.
Both C: and D: retain a separate **30 GiB** reserve. The monitor governs managed writers;
it is not an operating-system quota and does not constrain unrelated applications.

## Development

Python 3.12+, `psutil==7.2.2`, Java 21 and Node.js for the JavaScript syntax check:

```powershell
python -m control_room run --home "D:\A World for Two"
python -m unittest discover -s tests -v
python -m tools.pack validate
node --check control_room/static/app.js
```

Open **http://127.0.0.1:8765**. The backend binds only to loopback, checks Host/Origin
and requires a per-session token for all mutations. Never expose it through a public tunnel.

`catalog/selection.json` contains deliberate exact candidate choices. `tools.pack resolve`
generates the release lock and Packwiz metadata together; `tools.pack validate` detects
drift between them. Changes through Mod Manager are staged for review and cannot deploy
without the exact candidate's runtime acceptance and matching client publication.

## Reference workflow

`Kgray44/kg-minecraft-pack` was inspected **read-only**, at
`594e00cd63b6abdcc199928576d8682932a0d959`. Its Prism + Packwiz pre-launch workflow is
retained. The reference's JARs, shader ZIPs and side classifications were not copied blindly.
For example, Iris is client-only, and this candidate's current Sable requires newer Sodium
than the reference shader stack. See the generated inventory for the exact final decisions.
