#!/usr/bin/env python3
"""
seed-carl-domain.py

Seeds a Caddy-managed CARL domain into a customer's carl.json.
Idempotent. Safe to run on fresh setup, re-setup, and update.

Tracks seeded rules via a sidecar state file so we can distinguish
Caddy-shipped versions from customer-modified versions on subsequent runs.

Behavior on subsequent runs (per slug):
  - new rule (not in sidecar):           CREATE
  - existing, customer unchanged:        UPDATE if shipped version > sidecar version
  - existing, customer modified:         PRESERVE + warn (DIVERGED)
  - in sidecar but missing in carl.json: RECREATE (customer deleted it)

Exit codes:
  0  success
  2  schema version mismatch (carl.json or rules file from a future version)
  3  rules file missing or unreadable
  4  carl.json unreadable (parse error on existing file)

Output format: one line per rule, prefixed with action keyword, plus a
summary line at the end. Designed for shell-script consumption.

Known design choices and untested edges:
  1. Identification of Caddy-managed rules is via the sidecar's
     rule_id_in_carl mapping, NOT via the rules[].source field.
     We set source='caddy' for informational purposes; if carl-mcp
     ever strips unknown source values on its own writes, our
     idempotency still works.
  2. Caddy-shipped rules bypass carl-mcp's staging workflow
     (carl_v2_stage_proposal / approve_proposal). Intentional:
     these are vendor-shipped, not customer-proposed. Customers
     can still stage their own rules through the normal CARL UX;
     our domain coexists alongside.
  3. Legacy CARL manifest format (.carl/MANIFEST + per-domain files)
     is NOT handled. We assume customers who ran `npx carl-core`
     have the v2 carl.json format. A customer who imported old
     config will see Caddy's rules in carl.json but the legacy
     manifest may shadow them; recovery is to remove the manifest
     and re-run /caddy:carl-setup.
  4. Concurrent runs are not protected. /caddy:carl-setup is
     sequential by design; parallel runs are unlikely. If they
     happen, the second run may produce duplicate rule entries
     in carl.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_CARL_VERSION = 1
EXPECTED_RULES_SCHEMA = 1
DEFAULT_CARL_JSON = Path.home() / ".carl" / "carl.json"
DEFAULT_STATE_FILE = Path.home() / ".claude" / "caddy" / "carl-state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def empty_carl_json() -> dict:
    return {
        "version": EXPECTED_CARL_VERSION,
        "last_modified": None,
        "config": {
            "devmode": False,
            "post_compact_gate": True,
            "global_exclude": [],
        },
        "domains": {},
        "staging": [],
    }


def empty_state() -> dict:
    return {
        "schema_version": 1,
        "managed_rules": {},
    }


def ensure_domain(carl: dict, domain_meta: dict) -> dict:
    name = domain_meta["name"]
    domains = carl.setdefault("domains", {})
    if name not in domains:
        domains[name] = {
            "state": domain_meta.get("state", "active"),
            "always_on": domain_meta.get("always_on", True),
            "recall": domain_meta.get("recall", ["universal"]),
            "exclude": domain_meta.get("exclude", []),
            "rules": [],
            "decisions": [],
        }
    else:
        d = domains[name]
        d.setdefault("state", domain_meta.get("state", "active"))
        d.setdefault("always_on", domain_meta.get("always_on", True))
        d.setdefault("recall", domain_meta.get("recall", ["universal"]))
        d.setdefault("exclude", domain_meta.get("exclude", []))
        d.setdefault("rules", [])
        d.setdefault("decisions", [])
    return domains[name]


def next_rule_id(rules: list) -> int:
    if not rules:
        return 0
    return max(r.get("id", -1) for r in rules) + 1


def find_rule_by_id(rules: list, rule_id: int) -> dict | None:
    for r in rules:
        if r.get("id") == rule_id:
            return r
    return None


def seed(
    rules_file: Path,
    carl_json_path: Path,
    state_file_path: Path,
    dry_run: bool,
) -> int:
    # Read rules file (required)
    if not rules_file.exists():
        print(f"ERROR rules file not found: {rules_file}", file=sys.stderr)
        return 3
    try:
        rules_data = read_json(rules_file)
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR cannot read rules file: {e}", file=sys.stderr)
        return 3

    rules_schema = rules_data.get("schema_version")
    if rules_schema != EXPECTED_RULES_SCHEMA:
        print(
            f"ERROR rules file schema_version={rules_schema} but seeder expects {EXPECTED_RULES_SCHEMA}",
            file=sys.stderr,
        )
        return 2

    domain_meta = rules_data["domain"]
    shipped_rules = rules_data["rules"]

    # Read carl.json (create if missing)
    if carl_json_path.exists():
        try:
            carl = read_json(carl_json_path)
        except json.JSONDecodeError as e:
            print(f"ERROR cannot parse carl.json: {e}", file=sys.stderr)
            return 4
        carl_version = carl.get("version")
        if carl_version != EXPECTED_CARL_VERSION:
            print(
                f"ERROR carl.json version={carl_version} but seeder expects {EXPECTED_CARL_VERSION}. "
                f"Run /caddy:carl-setup to refresh Caddy's CARL handling, or contact support.",
                file=sys.stderr,
            )
            return 2
    else:
        carl = empty_carl_json()

    # Read sidecar state (create if missing)
    state = read_json(state_file_path) if state_file_path.exists() else empty_state()
    managed = state.setdefault("managed_rules", {})

    # Ensure domain exists with correct config
    domain = ensure_domain(carl, domain_meta)

    counts = {
        "created": 0,
        "updated": 0,
        "preserved_current": 0,
        "preserved_diverged": 0,
        "recreated": 0,
    }

    for shipped in shipped_rules:
        slug = shipped["slug"]
        shipped_text = shipped["text"]
        shipped_version = shipped["version"]
        shipped_hash = hash_text(shipped_text)

        record = managed.get(slug)

        if record is None:
            new_id = next_rule_id(domain["rules"])
            domain["rules"].append({
                "id": new_id,
                "text": shipped_text,
                "added": now_iso(),
                "last_reviewed": None,
                "source": "caddy",
            })
            managed[slug] = {
                "domain": domain_meta["name"],
                "rule_id_in_carl": new_id,
                "seeded_text_hash": shipped_hash,
                "shipped_version": shipped_version,
                "last_seeded": now_iso(),
            }
            counts["created"] += 1
            print(f"CREATED slug={slug} rule_id={new_id} version={shipped_version}")
            continue

        rule_id = record["rule_id_in_carl"]
        existing = find_rule_by_id(domain["rules"], rule_id)

        if existing is None:
            new_id = next_rule_id(domain["rules"])
            domain["rules"].append({
                "id": new_id,
                "text": shipped_text,
                "added": now_iso(),
                "last_reviewed": None,
                "source": "caddy",
            })
            record.update({
                "rule_id_in_carl": new_id,
                "seeded_text_hash": shipped_hash,
                "shipped_version": shipped_version,
                "last_seeded": now_iso(),
            })
            counts["recreated"] += 1
            print(f"RECREATED slug={slug} rule_id={new_id} version={shipped_version}")
            continue

        current_hash = hash_text(existing.get("text", ""))
        if current_hash != record["seeded_text_hash"]:
            counts["preserved_diverged"] += 1
            print(
                f"PRESERVED slug={slug} rule_id={rule_id} reason=local-modification "
                f"hint='Run /carl:manager to review or restore'"
            )
            continue

        if shipped_version > record.get("shipped_version", 0):
            existing["text"] = shipped_text
            existing["last_reviewed"] = now_iso()
            existing["source"] = "caddy"
            record["seeded_text_hash"] = shipped_hash
            record["shipped_version"] = shipped_version
            record["last_seeded"] = now_iso()
            counts["updated"] += 1
            print(f"UPDATED slug={slug} rule_id={rule_id} version={shipped_version}")
        else:
            counts["preserved_current"] += 1
            print(f"PRESERVED slug={slug} rule_id={rule_id} reason=already-current")

    if dry_run:
        print(
            f"DRY-RUN domain={domain_meta['name']} "
            f"created={counts['created']} "
            f"updated={counts['updated']} "
            f"preserved_current={counts['preserved_current']} "
            f"preserved_diverged={counts['preserved_diverged']} "
            f"recreated={counts['recreated']} "
            "(no writes performed)"
        )
        return 0

    carl["last_modified"] = now_iso()
    write_json(carl_json_path, carl)
    write_json(state_file_path, state)

    summary = (
        f"SUMMARY domain={domain_meta['name']} "
        f"created={counts['created']} "
        f"updated={counts['updated']} "
        f"preserved_current={counts['preserved_current']} "
        f"preserved_diverged={counts['preserved_diverged']} "
        f"recreated={counts['recreated']}"
    )
    print(summary)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed a Caddy-managed CARL domain into the customer's carl.json.",
    )
    parser.add_argument(
        "--rules-file",
        type=Path,
        required=True,
        help="Path to the Caddy rules JSON (e.g. carl-rules/caddy-safety.json).",
    )
    parser.add_argument(
        "--carl-json",
        type=Path,
        default=DEFAULT_CARL_JSON,
        help=f"Path to carl.json (default: {DEFAULT_CARL_JSON}).",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help=f"Path to Caddy's CARL sidecar state file (default: {DEFAULT_STATE_FILE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and compare, but do not write carl.json or state file.",
    )
    args = parser.parse_args()
    return seed(
        rules_file=args.rules_file,
        carl_json_path=args.carl_json,
        state_file_path=args.state_file,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
