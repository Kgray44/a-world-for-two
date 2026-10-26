"""Capture authoritative Modrinth metadata without downloading or redistributing mods.

Search results are leads, never automatic identity or compatibility decisions.
The checked-in lock is assembled only after reviewing these records and JAR metadata.
"""
from __future__ import annotations

import concurrent.futures
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.modrinth.com/v2"
UA = "Kgray44/a-world-for-two research/0.1 (github.com/Kgray44/a-world-for-two)"

IDENTITIES = {
    "farmers-delight": "farmers-delight", "farm-and-charm": "lets-do-farm-charm",
    "vinery": "lets-do-vinery", "steam-n-rails": "L3Jv0QZI",
    "central-kitchen": "create-central-kitchen", "slice-and-dice": "slice-and-dice",
    "ornithopter": "create-ornithopter-glider", "aeronautics": "create-aeronautics",
    "big-cannons": "create-big-cannons", "projectile-library": "ritchies-projectile-library",
    "tacz": "tacz-unofficial-neoforge", "iris": "iris", "distanthorizons": "distanthorizons",
    "dh-seedgen": "distant-horizons-seedgen", "bsl": "bsl-shaders",
    "complementary-reimagined": "complementary-reimagined",
    "complementary-unbound": "complementary-unbound", "biomes-weve-gone": "oh-the-biomes-weve-gone",
    "aztec-temple-ruins": "aztec-ruins", "moogs-temples-reimagined": "mtr-moogs-temples-reimagined",
}


def get(path: str):
    req = urllib.request.Request(API + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Metadata response exceeded 8 MiB")
        return json.loads(raw)


def investigate(item):
    key, name, group = item
    record = {"id": key, "requested": name, "group": group, "checked_at": datetime.now(timezone.utc).isoformat()}
    try:
        query = urllib.parse.urlencode({"query": name, "limit": 5})
        record["search"] = get("/search?" + query)["hits"]
        slug = IDENTITIES.get(key, key)
        try:
            record["project"] = get("/project/" + urllib.parse.quote(slug))
            params = urllib.parse.urlencode({"game_versions": json.dumps(["1.21.1"])})
            versions = get("/project/" + record["project"]["id"] + "/version?" + params)
            record["versions_1_21_1"] = versions
        except urllib.error.HTTPError as exc:
            record["identity_lookup_error"] = str(exc)
    except Exception as exc:
        record["error"] = str(exc)
    return record


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    requests = json.loads((ROOT / "catalog/requests.json").read_text())["requests"]
    if args.only:
        requests = [r for r in requests if r[0] in args.only]
    destination = ROOT / "evidence/research"
    destination.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        for record in executor.map(investigate, requests):
            raw = json.dumps(record, indent=2)
            if len(raw.encode()) > 8 * 1024 * 1024:
                raise ValueError("Record too large")
            (destination / (record["id"] + ".json")).write_text(raw + "\n", encoding="utf-8")
            compatible = [v for v in record.get("versions_1_21_1", []) if "neoforge" in v["loaders"]]
            print(json.dumps({"id": record["id"], "identity": record.get("project", {}).get("title"),
                              "compatible": [(v["id"], v["version_number"], v["version_type"],
                                              [f["filename"] for f in v["files"] if f.get("primary")])
                                             for v in compatible[:4]],
                              "leads": [(x["slug"], x["title"]) for x in record.get("search", [])[:3]],
                              "error": record.get("error")}), flush=True)
            time.sleep(0.05)


if __name__ == "__main__":
    main()
