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
    parser.add_argument(
        "--list-mode",
        choices=["default", "extend", "custom"],
        default="default",
        help="Ticker list mode",
    )
    parser.add_argument(
        "--custom-tickers",
        default="",
        help="Comma-separated custom tickers",
    )
    parser.add_argument(
        "--include-benchmarks",
        action="store_true",
        default=True,
        help="Include ACWI/S&P500/OMXC25 benchmarks",
    )
    parser.add_argument(
        "--no-benchmarks",
        action="store_true",
        help="Disable benchmark assets",
    )
    args = parser.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    include_benchmarks = False if args.no_benchmarks else bool(args.include_benchmarks)
    settings = {
        "list_mode": args.list_mode,
        "custom_tickers": args.custom_tickers,
        "include_benchmarks": include_benchmarks,
    }
    snapshot = build_snapshot(settings)
    out.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Snapshot written: {out}")
    print(f"Assets: {len(snapshot.get('assets', []))}")
    print(f"Generated at: {snapshot.get('generated_at')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
