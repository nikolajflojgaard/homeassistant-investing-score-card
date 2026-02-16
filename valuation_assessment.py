#!/usr/bin/env python3
"""Sector-specific valuation assessment based on scorecard results."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yfinance as yf

TICKERS = {
    "Nvidia": "NVDA",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Amazon": "AMZN",
    "Alphabet": "GOOGL",
    "Meta": "META",
    "Broadcom": "AVGO",
    "Tesla": "TSLA",
    "Berkshire Hathaway": "BRK-B",
    "Walmart": "WMT",
    "Eli Lilly": "LLY",
    "JPMorgan Chase": "JPM",
    "Visa": "V",
    "ExxonMobil": "XOM",
    "Johnson & Johnson": "JNJ",
    "Novo Nordisk": "NVO",
    "Nordea": "NDA-FI.HE",
    "DSV": "DSV.CO",
    "Danske Bank": "DANSKE.CO",
    "A.P. Moller - Maersk": "MAERSK-B.CO",
}

BROAD_BENCHMARKS = [
    {
        "company": "MSCI World ACWI (benchmark)",
        "ticker_price": "ACWI",
        "ticker_valuation": "ACWI",
        "fair_pe": 20.0,
    },
    {
        "company": "S&P 500 (benchmark)",
        "ticker_price": "^GSPC",
        "ticker_valuation": "SPY",  # proxy for index PE
        "fair_pe": 21.0,
    },
    {
        "company": "OMXC25 (benchmark)",
        "ticker_price": "^OMXC25",
        "ticker_valuation": "XACTC25.CO",  # proxy ETF for index PE
        "fair_pe": 17.5,
    },
]


def safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x:
        return None
    return x


def model_for_sector(sector: str, industry: str) -> str:
    s = (sector or "").lower()
    i = (industry or "").lower()
    if "credit services" in i or "payment" in i:
        return "pe"
    if "financial" in s or "bank" in s or "insurance" in s:
        return "pb"
    if "energy" in s or "oil" in s or "gas" in s:
        return "ev_ebitda"
    if "industrial" in s or "transport" in s or "shipping" in s:
        return "ev_ebitda"
    return "pe"


def valuation_style(sector: str, industry: str) -> str:
    s = (sector or "").lower()
    i = (industry or "").lower()
    if "software" in i or "semiconductor" in i or "internet" in i:
        return "tech_hypergrowth"
    if "technology" in s or "electronic" in i:
        return "tech_quality"
    if "financial" in s or "bank" in s or "insurance" in s:
        return "financials"
    if "energy" in s or "oil" in i or "gas" in i:
        return "energy"
    if "industrial" in s or "transport" in s or "shipping" in i:
        return "industrials"
    if "healthcare" in s or "pharmaceutical" in i or "drug" in i:
        return "healthcare"
    return "broad_market"


def fair_multiple(score: float, model: str, style: str) -> float:
    if model == "pe" and style == "tech_hypergrowth":
        return 14.0 + (score * 0.42)  # 14 -> 56
    if model == "pe" and style == "tech_quality":
        return 11.0 + (score * 0.34)  # 11 -> 45
    if model == "pe" and style == "healthcare":
        return 9.0 + (score * 0.30)  # 9 -> 39
    if model == "pe":
        return 7.0 + (score * 0.26)  # 7 -> 33
    if model == "pb":
        return 0.6 + (score * 0.018)  # 0.6 -> 2.4
    if model == "ev_ebitda":
        return 3.0 + (score * 0.11)  # 3 -> 14
    return 10.0


def valuation_label(ratio: Optional[float], style: str) -> str:
    if ratio is None:
        return "N/A"
    # Wider fair band for tech, where higher multiples can persist.
    fair_low, fair_high = 0.85, 1.15
    if style in {"tech_hypergrowth", "tech_quality"}:
        fair_low, fair_high = 0.75, 1.30
    if ratio <= fair_low:
        return "Undervalued"
    if ratio >= fair_high:
        return "Overvalued"
    return "Fair"


def load_scores(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def compute(input_csv: Path) -> List[Dict[str, str]]:
    rows = load_scores(input_csv)

    out = []
    for r in rows:
        company = r["company"]
        ticker = TICKERS.get(company)
        score = safe_float(r.get("score_total"))
        if score is None:
            score = 50.0

        price = None
        sector = ""
        industry = ""
        model = "pe"
        style = "broad_market"
        actual_mult = None

        if ticker:
            t = yf.Ticker(ticker)
            fast = getattr(t, "fast_info", None)
            if fast is not None:
                price = safe_float(getattr(fast, "last_price", None))

            info = t.info or {}
            sector = str(info.get("sector", ""))
            industry = str(info.get("industry", ""))
            model = model_for_sector(sector, industry)
            style = valuation_style(sector, industry)

            trailing_pe = safe_float(info.get("trailingPE"))
            pb = safe_float(info.get("priceToBook"))
            ev_ebitda = safe_float(info.get("enterpriseToEbitda"))

            if trailing_pe is not None and trailing_pe <= 0:
                trailing_pe = None
            if pb is not None and pb <= 0:
                pb = None
            if ev_ebitda is not None and ev_ebitda <= 0:
                ev_ebitda = None

            if model == "pe":
                actual_mult = trailing_pe
            elif model == "pb":
                actual_mult = pb
            else:
                actual_mult = ev_ebitda

            # Fallback if chosen multiple is unavailable.
            if actual_mult is None:
                if trailing_pe is not None:
                    model = "pe"
                    actual_mult = trailing_pe
                elif pb is not None:
                    model = "pb"
                    actual_mult = pb
                elif ev_ebitda is not None:
                    model = "ev_ebitda"
                    actual_mult = ev_ebitda

            if model == "pb" and actual_mult is not None and actual_mult < 0.3:
                actual_mult = trailing_pe if trailing_pe is not None else actual_mult
                if trailing_pe is not None:
                    model = "pe"

        fair_mult = fair_multiple(score, model, style)
        ratio = None
        if actual_mult is not None and fair_mult > 0:
            ratio = actual_mult / fair_mult
        fair_price = None
        valuation_gap_pct = None
        if ratio is not None and price is not None and ratio > 0:
            fair_price = price / ratio
            valuation_gap_pct = ((fair_price / price) - 1.0) * 100.0

        out.append(
            {
                **r,
                "ticker": ticker or "",
                "sector": sector,
                "industry": industry,
                "valuation_style": style,
                "valuation_model": model.upper().replace("_", "/"),
                "current_price": "" if price is None else f"{price:.2f}",
                "actual_multiple": "" if actual_mult is None else f"{actual_mult:.2f}",
                "fair_multiple": f"{fair_mult:.2f}",
                "multiple_ratio": "" if ratio is None else f"{ratio:.2f}",
                "fair_price": "" if fair_price is None else f"{fair_price:.2f}",
                "valuation_gap_pct": "" if valuation_gap_pct is None else f"{valuation_gap_pct:.1f}",
                "price_assessment": valuation_label(ratio, style),
            }
        )

    # Add broad benchmark lines as row 21 and 22.
    for b in BROAD_BENCHMARKS:
        p_t = yf.Ticker(b["ticker_price"])
        v_t = yf.Ticker(b["ticker_valuation"])

        fast = getattr(p_t, "fast_info", None)
        price = safe_float(getattr(fast, "last_price", None)) if fast is not None else None

        v_info = v_t.info or {}
        pe = safe_float(v_info.get("trailingPE"))
        if pe is not None and pe <= 0:
            pe = None

        fair_mult = float(b["fair_pe"])
        ratio = (pe / fair_mult) if (pe is not None and fair_mult > 0) else None
        fair_price = (price / ratio) if (ratio is not None and price is not None and ratio > 0) else None
        valuation_gap_pct = ((fair_price / price) - 1.0) * 100.0 if (fair_price is not None and price not in (None, 0)) else None

        out.append(
            {
                "company": b["company"],
                "index": "Benchmark",
                "ir_url": "",
                "latest_report_date": "",
                "latest_report_url": "",
                "prior_report_date": "",
                "prior_report_url": "",
                "revenue_yoy_pct": "",
                "eps_yoy_pct": "",
                "op_margin_latest_pct": "",
                "op_margin_prior_pct": "",
                "guidance_change": "",
                "fcf_yoy_pct": "",
                "net_debt_to_ebitda": "",
                "data_completeness_pct": "",
                "score_growth_revenue": "",
                "score_growth_eps": "",
                "score_profit_margin_level": "",
                "score_profit_margin_yoy": "",
                "score_guidance": "",
                "score_capital_fcf": "",
                "score_capital_leverage": "",
                "score_total": "",
                "grade": "N/A",
                "ticker": b["ticker_price"],
                "sector": "Broad Market Index",
                "industry": "Diversified",
                "valuation_style": "broad_market",
                "valuation_model": "PE",
                "current_price": "" if price is None else f"{price:.2f}",
                "actual_multiple": "" if pe is None else f"{pe:.2f}",
                "fair_multiple": f"{fair_mult:.2f}",
                "multiple_ratio": "" if ratio is None else f"{ratio:.2f}",
                "fair_price": "" if fair_price is None else f"{fair_price:.2f}",
                "valuation_gap_pct": "" if valuation_gap_pct is None else f"{valuation_gap_pct:.1f}",
                "price_assessment": valuation_label(ratio, "broad_market"),
            }
        )

    return out


def write_csv(rows: List[Dict[str, str]], path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_markdown(rows: List[Dict[str, str]], path: Path) -> None:
    asof = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"_As of: {asof}_",
        "",
        "| Company | Score | Grade | Price | Fair Price | Upside/Downside % | Model | Actual | Fair | Ratio | Assessment |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            "| {company} | {score_total} | {grade} | {current_price} | {fair_price} | {valuation_gap_pct} | {valuation_model} | {actual_multiple} | {fair_multiple} | {multiple_ratio} | {price_assessment} |".format(
                **r
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--markdown", required=True, type=Path)
    args = ap.parse_args()

    rows = compute(args.input)
    write_csv(rows, args.output)
    write_markdown(rows, args.markdown)


if __name__ == "__main__":
    main()
