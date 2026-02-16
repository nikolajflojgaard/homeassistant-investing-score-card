#!/usr/bin/env python3
"""Score companies from latest report vs same report last year."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class Weights:
    revenue_yoy: float = 15.0
    eps_yoy: float = 15.0
    op_margin_level: float = 12.0
    op_margin_yoy: float = 13.0
    guidance: float = 25.0
    fcf_yoy: float = 10.0
    net_debt_to_ebitda: float = 10.0


WEIGHTS = Weights()


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def piecewise_score(value: float, bands: List[tuple]) -> float:
    """Map value to a 0..1 score using sorted (threshold, score) bands."""
    for threshold, score in bands:
        if value <= threshold:
            return score
    return bands[-1][1]


def score_growth_revenue_yoy(v: float) -> float:
    bands = [
        (-20, 0.00),
        (-10, 0.10),
        (0, 0.30),
        (5, 0.55),
        (10, 0.70),
        (15, 0.82),
        (25, 0.92),
        (10_000, 1.00),
    ]
    return piecewise_score(v, bands) * WEIGHTS.revenue_yoy


def score_growth_eps_yoy(v: float) -> float:
    bands = [
        (-40, 0.00),
        (-20, 0.10),
        (0, 0.30),
        (10, 0.55),
        (20, 0.72),
        (35, 0.85),
        (50, 0.94),
        (10_000, 1.00),
    ]
    return piecewise_score(v, bands) * WEIGHTS.eps_yoy


def score_profitability_margin_level(v: float) -> float:
    bands = [
        (0, 0.00),
        (5, 0.15),
        (10, 0.30),
        (15, 0.50),
        (20, 0.70),
        (25, 0.83),
        (30, 0.93),
        (10_000, 1.00),
    ]
    return piecewise_score(v, bands) * WEIGHTS.op_margin_level


def score_profitability_margin_yoy(v_pp: float) -> float:
    bands = [
        (-8, 0.00),
        (-4, 0.12),
        (-2, 0.28),
        (0, 0.45),
        (1, 0.62),
        (2, 0.76),
        (4, 0.90),
        (10_000, 1.00),
    ]
    return piecewise_score(v_pp, bands) * WEIGHTS.op_margin_yoy


def score_guidance(v: str) -> float:
    m = {
        "cut": 0.0,
        "lowered": 0.0,
        "unchanged": 12.0,
        "maintained": 12.0,
        "raised": 25.0,
    }
    return m.get(v.strip().lower(), 12.0)


def score_fcf_yoy(v: float) -> float:
    bands = [
        (-50, 0.00),
        (-25, 0.15),
        (-10, 0.32),
        (0, 0.50),
        (10, 0.66),
        (20, 0.80),
        (35, 0.92),
        (10_000, 1.00),
    ]
    return piecewise_score(v, bands) * WEIGHTS.fcf_yoy


def score_net_debt_to_ebitda(v: float) -> float:
    bands = [
        (0.0, 1.00),
        (1.0, 0.88),
        (2.0, 0.72),
        (3.0, 0.52),
        (4.0, 0.30),
        (5.0, 0.15),
        (10_000, 0.00),
    ]
    return piecewise_score(v, bands) * WEIGHTS.net_debt_to_ebitda


def to_grade(score: float) -> str:
    scale = [
        (97, "A+"),
        (93, "A"),
        (90, "A-"),
        (87, "B+"),
        (83, "B"),
        (80, "B-"),
        (77, "C+"),
        (73, "C"),
        (70, "C-"),
        (67, "D+"),
        (63, "D"),
        (60, "D-"),
    ]
    for threshold, grade in scale:
        if score >= threshold:
            return grade
    return "F"


def f(row: Dict[str, str], key: str) -> float:
    return float(row.get(key, "").strip())


def has_value(row: Dict[str, str], key: str) -> bool:
    return row.get(key, "").strip() != ""


def compute_row(row: Dict[str, str]) -> Dict[str, str]:
    required_meta = ["prior_report_date", "prior_report_url", "guidance_change"]
    required_numeric = [
        "revenue_yoy_pct",
        "eps_yoy_pct",
        "op_margin_latest_pct",
        "op_margin_prior_pct",
        "fcf_yoy_pct",
        "net_debt_to_ebitda",
    ]
    present_meta = sum(1 for k in required_meta if has_value(row, k))
    present_numeric = sum(1 for k in required_numeric if has_value(row, k))
    completeness = round(((present_meta + present_numeric) / (len(required_meta) + len(required_numeric))) * 100.0, 1)

    out = dict(row)
    out["data_completeness_pct"] = f"{completeness:.1f}"

    components = []
    if has_value(row, "revenue_yoy_pct"):
        rev_s = score_growth_revenue_yoy(f(row, "revenue_yoy_pct"))
        components.append((rev_s, WEIGHTS.revenue_yoy))
        out["score_growth_revenue"] = f"{rev_s:.1f}"
    else:
        out["score_growth_revenue"] = ""

    if has_value(row, "eps_yoy_pct"):
        eps_s = score_growth_eps_yoy(f(row, "eps_yoy_pct"))
        components.append((eps_s, WEIGHTS.eps_yoy))
        out["score_growth_eps"] = f"{eps_s:.1f}"
    else:
        out["score_growth_eps"] = ""

    if has_value(row, "op_margin_latest_pct") and has_value(row, "op_margin_prior_pct"):
        op_now = f(row, "op_margin_latest_pct")
        op_prev = f(row, "op_margin_prior_pct")
        op_lvl_s = score_profitability_margin_level(op_now)
        op_yoy_s = score_profitability_margin_yoy(op_now - op_prev)
        components.append((op_lvl_s, WEIGHTS.op_margin_level))
        components.append((op_yoy_s, WEIGHTS.op_margin_yoy))
        out["score_profit_margin_level"] = f"{op_lvl_s:.1f}"
        out["score_profit_margin_yoy"] = f"{op_yoy_s:.1f}"
    else:
        out["score_profit_margin_level"] = ""
        out["score_profit_margin_yoy"] = ""

    if has_value(row, "guidance_change"):
        gui_s = score_guidance(row.get("guidance_change", "unchanged"))
        components.append((gui_s, WEIGHTS.guidance))
        out["score_guidance"] = f"{gui_s:.1f}"
    else:
        out["score_guidance"] = ""

    if has_value(row, "fcf_yoy_pct"):
        fcf_s = score_fcf_yoy(f(row, "fcf_yoy_pct"))
        components.append((fcf_s, WEIGHTS.fcf_yoy))
        out["score_capital_fcf"] = f"{fcf_s:.1f}"
    else:
        out["score_capital_fcf"] = ""

    if has_value(row, "net_debt_to_ebitda"):
        nde_s = score_net_debt_to_ebitda(f(row, "net_debt_to_ebitda"))
        components.append((nde_s, WEIGHTS.net_debt_to_ebitda))
        out["score_capital_leverage"] = f"{nde_s:.1f}"
    else:
        out["score_capital_leverage"] = ""

    if not components:
        out["score_total"] = ""
        out["grade"] = "N/A"
        return out

    raw_points = sum(score for score, _ in components)
    max_points = sum(weight for _, weight in components)
    normalized_total = (raw_points / max_points) * 100.0
    total = clamp(normalized_total, 0.0, 100.0)
    out["score_total"] = f"{total:.1f}"
    out["grade"] = to_grade(total)
    return out


def write_markdown(rows: List[Dict[str, str]], path: Path) -> None:
    lines = [
        "| Company | Index | Completeness | Score | Grade | Latest report | Prior comparable |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for r in rows:
        latest = f"[{r['latest_report_date']}]({r['latest_report_url']})"
        if r["prior_report_date"] and r["prior_report_url"]:
            prior = f"[{r['prior_report_date']}]({r['prior_report_url']})"
        else:
            prior = "-"
        lines.append(
            f"| {r['company']} | {r['index']} | {r['data_completeness_pct']}% | {r['score_total']} | {r['grade']} | {latest} | {prior} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--markdown", required=False, type=Path)
    args = ap.parse_args()

    with args.input.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        rows = [compute_row(r) for r in reader]

    if not rows:
        raise SystemExit("Input file has no rows.")

    fieldnames = list(rows[0].keys())
    with args.output.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    if args.markdown:
        write_markdown(rows, args.markdown)


if __name__ == "__main__":
    main()
