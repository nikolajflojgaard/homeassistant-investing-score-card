#!/usr/bin/env python3
"""Generate a weekly investing snapshot JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "investing_score_card"))

from engine import build_snapshot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "weekly_snapshot.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    snapshot = build_snapshot()
    out.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Snapshot written: {out}")
    print(f"Assets: {len(snapshot.get('assets', []))}")
    print(f"Generated at: {snapshot.get('generated_at')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
