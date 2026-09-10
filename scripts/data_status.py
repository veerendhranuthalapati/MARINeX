"""Data manifest status reporter.

Usage:
    python scripts/data_status.py               # catalog table
    python scripts/data_status.py --json        # machine-readable summary
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.data.manifest import catalog, catalog_summary

CLEAN = "\033[92m"
WARN = "\033[93m"
END = "\033[0m"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    manifests = catalog()
    summary = catalog_summary(manifests)

    if args.json:
        print(json.dumps({"datasets": manifests, "summary": summary}, indent=2))
        return 0

    print(f"{'dataset_id':42} {'samples':>7} {'status':8} {'local_bytes':>14}  checksum")
    print("-" * 100)
    for m in manifests:
        mark = CLEAN if m["status"] == "local" else WARN
        print(f"{mark}{m['dataset_id']:42} {m['n_samples']:>7} {m['status']:8} {m['size_bytes']:>14}  {m['checksum'][:16]}...{END}")
    print("-" * 100)
    print(f"total datasets: {summary['counts']['total']} | local: {summary['counts']['local']} | remote-only: {summary['counts']['remote']} | missing: {summary['counts']['missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())