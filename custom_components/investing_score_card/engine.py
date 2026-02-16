"""Core investment scoring and valuation engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import yfinance as yf


@dataclass(frozen=True)
class AssetConfig:
    name: str
    ticker: str
    index_name: str
    benchmark: bool = False
    valuation_ticker: str | None = None
    benchmark_fair_pe: float | None = None


DEFAULT_COMPANY_ASSETS: list[AssetConfig] = [
    AssetConfig("Nvidia", "NVDA", "S&P 500"),
    AssetConfig("Apple", "AAPL", "S&P 500"),
    AssetConfig("Microsoft", "MSFT", "S&P 500"),
    AssetConfig("Amazon", "AMZN", "S&P 500"),
    AssetConfig("Alphabet", "GOOGL", "S&P 500"),
    AssetConfig("Meta", "META", "S&P 500"),
    AssetConfig("Broadcom", "AVGO", "S&P 500"),
    AssetConfig("Tesla", "TSLA", "S&P 500"),
    AssetConfig("Berkshire Hathaway", "BRK-B", "S&P 500"),
    AssetConfig("Walmart", "WMT", "S&P 500"),
    AssetConfig("Eli Lilly", "LLY", "S&P 500"),
    AssetConfig("JPMorgan Chase", "JPM", "S&P 500"),
    AssetConfig("Visa", "V", "S&P 500"),
    AssetConfig("ExxonMobil", "XOM", "S&P 500"),
    AssetConfig("Johnson & Johnson", "JNJ", "S&P 500"),
    AssetConfig("Novo Nordisk", "NVO", "OMXC25"),
    AssetConfig("Nordea", "NDA-FI.HE", "OMXC25"),
    AssetConfig("DSV", "DSV.CO", "OMXC25"),
    AssetConfig("Danske Bank", "DANSKE.CO", "OMXC25"),
    AssetConfig("A.P. Moller - Maersk", "MAERSK-B.CO", "OMXC25"),
]

DEFAULT_BENCHMARK_ASSETS: list[AssetConfig] = [
    AssetConfig("MSCI World ACWI (benchmark)", "ACWI", "Benchmark", True, "ACWI", 20.0),
    AssetConfig("S&P 500 (benchmark)", "^GSPC", "Benchmark", True, "SPY", 21.0),
    AssetConfig("OMXC25 (benchmark)", "^OMXC25", "Benchmark", True, "XACTC25.CO", 17.5),
]


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out:
        return None
    return out


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        out = int(value)
    except (TypeError, ValueError):
        return None
    return out


def _parse_custom_tickers(raw: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for part in (raw or "").split(","):
        ticker = part.strip().upper()
        if not ticker:
            continue
        if ticker in seen:
            continue
        seen.add(ticker)
        items.append(ticker)
    return items


def _resolve_assets(settings: dict[str, Any] | None) -> list[AssetConfig]:
    cfg = settings or {}
    list_mode = str(cfg.get("list_mode", "default") or "default").strip().lower()
    include_benchmarks = bool(cfg.get("include_benchmarks", True))
    custom_tickers = _parse_custom_tickers(str(cfg.get("custom_tickers", "") or ""))
    custom_assets = [AssetConfig(ticker, ticker, "Custom") for ticker in custom_tickers]

    if list_mode == "custom":
        selected = custom_assets
    elif list_mode == "extend":
        selected = [*DEFAULT_COMPANY_ASSETS, *custom_assets]
    else:
        selected = list(DEFAULT_COMPANY_ASSETS)

    if include_benchmarks:
        selected = [*selected, *DEFAULT_BENCHMARK_ASSETS]
    return selected


def _next_earnings_from_info(info: dict[str, Any]) -> tuple[str, int | None]:
    candidates: list[int] = []
    for key in ("earningsTimestampStart", "earningsTimestamp", "earningsTimestampEnd"):
        ts = _safe_int(info.get(key))
        if ts is not None and ts > 0:
            candidates.append(ts)

    earnings_date = info.get("earningsDate")
    if isinstance(earnings_date, list):
        for item in earnings_date:
            ts = _safe_int(item)
            if ts is not None and ts > 0:
                candidates.append(ts)
    else:
        ts = _safe_int(earnings_date)
        if ts is not None and ts > 0:
            candidates.append(ts)

    if not candidates:
        return ("", None)

    now_ts = int(datetime.now(timezone.utc).timestamp())
    future = sorted(ts for ts in candidates if ts >= now_ts)
    chosen = future[0] if future else sorted(candidates)[-1]
    iso = datetime.fromtimestamp(chosen, tz=timezone.utc).isoformat()
    return (iso, chosen)


def _pick(df: Any, names: list[str], col: Any) -> float | None:
    if df is None or getattr(df, "empty", True) or col is None:
        return None
    for name in names:
        if name in df.index and col in df.columns:
            return _safe_float(df.at[name, col])
    return None


def _cols_for(df: Any) -> tuple[Any | None, Any | None]:
    if df is None or getattr(df, "empty", True):
        return (None, None)
    cols = list(df.columns)
    if len(cols) >= 5:
        return (cols[0], cols[4])
    if len(cols) >= 2:
        return (cols[0], cols[1])
    return (None, None)


def _yoy(now: float | None, prev: float | None) -> float | None:
    if now is None or prev is None or prev == 0:
        return None
    return ((now - prev) / abs(prev)) * 100.0


def _model_for_sector(sector: str, industry: str) -> str:
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


def _valuation_style(sector: str, industry: str) -> str:
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


def _fair_multiple(score: float, model: str, style: str, bench_fair_pe: float | None) -> float:
    if bench_fair_pe is not None and model == "pe":
        return bench_fair_pe
    if model == "pe" and style == "tech_hypergrowth":
        return 14.0 + (score * 0.42)
    if model == "pe" and style == "tech_quality":
        return 11.0 + (score * 0.34)
    if model == "pe" and style == "healthcare":
        return 9.0 + (score * 0.30)
    if model == "pe":
        return 7.0 + (score * 0.26)
    if model == "pb":
        return 0.6 + (score * 0.018)
    if model == "ev_ebitda":
        return 3.0 + (score * 0.11)
    return 10.0


def _valuation_label(ratio: float | None, style: str) -> str:
    if ratio is None:
        return "N/A"
    low = 0.85
    high = 1.15
    if style in {"tech_hypergrowth", "tech_quality"}:
        low = 0.75
        high = 1.30
    if ratio <= low:
        return "Undervalued"
    if ratio >= high:
        return "Overvalued"
    return "Fair"


def _piecewise(value: float, bands: list[tuple[float, float]]) -> float:
    for threshold, score in bands:
        if value <= threshold:
            return score
    return bands[-1][1]


def _score_component_value(value: float, bands: list[tuple[float, float]], weight: float) -> float:
    return _piecewise(value, bands) * weight


def _grade(score: float) -> str:
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
    for threshold, label in scale:
        if score >= threshold:
            return label
    return "F"


def _compute_score(metrics: dict[str, float | None]) -> dict[str, Any]:
    # 30 growth, 25 profitability, 25 guidance, 20 capital.
    components: dict[str, float] = {}
    available_weights = 0.0
    raw_points = 0.0

    rev = metrics.get("revenue_yoy_pct")
    if rev is not None:
        s = _score_component_value(
            rev,
            [(-20, 0.00), (-10, 0.10), (0, 0.30), (5, 0.55), (10, 0.70), (15, 0.82), (25, 0.92), (10_000, 1.00)],
            15.0,
        )
        components["growth_revenue"] = round(s, 1)
        raw_points += s
        available_weights += 15.0

    eps = metrics.get("eps_yoy_pct")
    if eps is not None:
        s = _score_component_value(
            eps,
            [(-40, 0.00), (-20, 0.10), (0, 0.30), (10, 0.55), (20, 0.72), (35, 0.85), (50, 0.94), (10_000, 1.00)],
            15.0,
        )
        components["growth_eps"] = round(s, 1)
        raw_points += s
        available_weights += 15.0

    op_margin = metrics.get("op_margin_latest_pct")
    op_margin_prior = metrics.get("op_margin_prior_pct")
    if op_margin is not None and op_margin_prior is not None:
        s_lvl = _score_component_value(
            op_margin,
            [(0, 0.00), (5, 0.15), (10, 0.30), (15, 0.50), (20, 0.70), (25, 0.83), (30, 0.93), (10_000, 1.00)],
            12.0,
        )
        s_yoy = _score_component_value(
            op_margin - op_margin_prior,
            [(-8, 0.00), (-4, 0.12), (-2, 0.28), (0, 0.45), (1, 0.62), (2, 0.76), (4, 0.90), (10_000, 1.00)],
            13.0,
        )
        components["profit_margin_level"] = round(s_lvl, 1)
        components["profit_margin_yoy"] = round(s_yoy, 1)
        raw_points += s_lvl + s_yoy
        available_weights += 25.0

    # Guidance fallback (without earnings call parsing) defaults to unchanged.
    guidance_points = 12.0
    components["guidance"] = guidance_points
    raw_points += guidance_points
    available_weights += 25.0

    fcf = metrics.get("fcf_yoy_pct")
    if fcf is not None:
        s = _score_component_value(
            fcf,
            [(-50, 0.00), (-25, 0.15), (-10, 0.32), (0, 0.50), (10, 0.66), (20, 0.80), (35, 0.92), (10_000, 1.00)],
            10.0,
        )
        components["capital_fcf"] = round(s, 1)
        raw_points += s
        available_weights += 10.0

    nde = metrics.get("net_debt_to_ebitda")
    if nde is not None:
        s = _score_component_value(
            nde,
            [(0.0, 1.00), (1.0, 0.88), (2.0, 0.72), (3.0, 0.52), (4.0, 0.30), (5.0, 0.15), (10_000, 0.00)],
            10.0,
        )
        components["capital_leverage"] = round(s, 1)
        raw_points += s
        available_weights += 10.0

    total = 0.0 if available_weights == 0 else min(100.0, max(0.0, (raw_points / available_weights) * 100.0))
    return {
        "score_total": round(total, 1),
        "grade": _grade(total),
        "components": components,
        "data_completeness_pct": round((available_weights / 100.0) * 100.0, 1),
    }


def _extract_financial_metrics(ticker: str) -> dict[str, Any]:
    t = yf.Ticker(ticker)
    info = t.info or {}
    fast = getattr(t, "fast_info", None)
    last_price = _safe_float(getattr(fast, "last_price", None)) if fast is not None else None

    inc = t.quarterly_income_stmt
    cf = t.quarterly_cashflow
    bs = t.quarterly_balance_sheet
    if inc is None or getattr(inc, "empty", True):
        inc = t.income_stmt
    if cf is None or getattr(cf, "empty", True):
        cf = t.cashflow
    if bs is None or getattr(bs, "empty", True):
        bs = t.balance_sheet

    inc_now_col, inc_prev_col = _cols_for(inc)
    cf_now_col, cf_prev_col = _cols_for(cf)
    bs_now_col, _ = _cols_for(bs)

    rev_now = _pick(inc, ["Total Revenue", "Operating Revenue"], inc_now_col)
    rev_prev = _pick(inc, ["Total Revenue", "Operating Revenue"], inc_prev_col)
    eps_now = _pick(inc, ["Diluted EPS", "Basic EPS"], inc_now_col)
    eps_prev = _pick(inc, ["Diluted EPS", "Basic EPS"], inc_prev_col)
    op_now = _pick(inc, ["Total Operating Income As Reported", "Operating Income"], inc_now_col)
    op_prev = _pick(inc, ["Total Operating Income As Reported", "Operating Income"], inc_prev_col)
    ebitda_now = _pick(inc, ["EBITDA", "Normalized EBITDA"], inc_now_col)
    fcf_now = _pick(cf, ["Free Cash Flow"], cf_now_col)
    fcf_prev = _pick(cf, ["Free Cash Flow"], cf_prev_col)
    net_debt = _pick(bs, ["Net Debt", "Total Debt"], bs_now_col)

    op_margin_latest = (op_now / rev_now * 100.0) if op_now is not None and rev_now not in (None, 0) else None
    op_margin_prior = (op_prev / rev_prev * 100.0) if op_prev is not None and rev_prev not in (None, 0) else None

    net_debt_to_ebitda = None
    if net_debt is not None and ebitda_now not in (None, 0):
        net_debt_to_ebitda = max(0.0, net_debt / (ebitda_now * 4.0))

    next_earnings_iso, next_earnings_ts = _next_earnings_from_info(info)

    return {
        "sector": str(info.get("sector", "")),
        "industry": str(info.get("industry", "")),
        "price": last_price,
        "trailing_pe": _safe_float(info.get("trailingPE")),
        "price_to_book": _safe_float(info.get("priceToBook")),
        "enterprise_to_ebitda": _safe_float(info.get("enterpriseToEbitda")),
        "latest_period": str(inc_now_col.date()) if inc_now_col is not None else "",
        "prior_period": str(inc_prev_col.date()) if inc_prev_col is not None else "",
        "revenue_yoy_pct": _yoy(rev_now, rev_prev),
        "eps_yoy_pct": _yoy(eps_now, eps_prev),
        "op_margin_latest_pct": op_margin_latest,
        "op_margin_prior_pct": op_margin_prior,
        "fcf_yoy_pct": _yoy(fcf_now, fcf_prev),
        "net_debt_to_ebitda": net_debt_to_ebitda,
        "next_earnings_iso": next_earnings_iso,
        "next_earnings_ts": next_earnings_ts,
    }


def _compute_company(asset: AssetConfig) -> dict[str, Any]:
    m = _extract_financial_metrics(asset.ticker)
    score = _compute_score(m)

    model = _model_for_sector(m["sector"], m["industry"])
    style = _valuation_style(m["sector"], m["industry"])

    trailing_pe = m["trailing_pe"]
    pb = m["price_to_book"]
    ev_ebitda = m["enterprise_to_ebitda"]
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

    if actual_mult is None:
        if trailing_pe is not None:
            model, actual_mult = "pe", trailing_pe
        elif pb is not None:
            model, actual_mult = "pb", pb
        elif ev_ebitda is not None:
            model, actual_mult = "ev_ebitda", ev_ebitda

    fair_mult = _fair_multiple(score["score_total"], model, style, None)
    ratio = (actual_mult / fair_mult) if actual_mult is not None and fair_mult > 0 else None
    fair_price = (m["price"] / ratio) if ratio is not None and m["price"] is not None and ratio > 0 else None
    valuation_gap_pct = ((fair_price / m["price"]) - 1.0) * 100.0 if fair_price is not None and m["price"] not in (None, 0) else None

    assessment = _valuation_label(ratio, style)
    rank_bonus = 30 if assessment == "Undervalued" else (10 if assessment == "Fair" else -20)
    opportunity_score = score["score_total"] + rank_bonus

    return {
        "name": asset.name,
        "ticker": asset.ticker,
        "index": asset.index_name,
        "benchmark": False,
        "latest_period": m["latest_period"],
        "prior_period": m["prior_period"],
        "sector": m["sector"],
        "industry": m["industry"],
        "price": round(m["price"], 2) if m["price"] is not None else None,
        "valuation_model": model.upper().replace("_", "/"),
        "valuation_style": style,
        "actual_multiple": round(actual_mult, 2) if actual_mult is not None else None,
        "fair_multiple": round(fair_mult, 2),
        "multiple_ratio": round(ratio, 2) if ratio is not None else None,
        "fair_price": round(fair_price, 2) if fair_price is not None else None,
        "valuation_gap_pct": round(valuation_gap_pct, 1) if valuation_gap_pct is not None else None,
        "assessment": assessment,
        "opportunity_score": round(opportunity_score, 1),
        "score_total": score["score_total"],
        "grade": score["grade"],
        "data_completeness_pct": score["data_completeness_pct"],
        "components": score["components"],
        "metrics": {
            "revenue_yoy_pct": round(m["revenue_yoy_pct"], 1) if m["revenue_yoy_pct"] is not None else None,
            "eps_yoy_pct": round(m["eps_yoy_pct"], 1) if m["eps_yoy_pct"] is not None else None,
            "op_margin_latest_pct": round(m["op_margin_latest_pct"], 1) if m["op_margin_latest_pct"] is not None else None,
            "op_margin_prior_pct": round(m["op_margin_prior_pct"], 1) if m["op_margin_prior_pct"] is not None else None,
            "fcf_yoy_pct": round(m["fcf_yoy_pct"], 1) if m["fcf_yoy_pct"] is not None else None,
            "net_debt_to_ebitda": round(m["net_debt_to_ebitda"], 2) if m["net_debt_to_ebitda"] is not None else None,
        },
        "next_earnings_iso": m.get("next_earnings_iso", ""),
        "next_earnings_ts": m.get("next_earnings_ts"),
    }


def _compute_benchmark(asset: AssetConfig) -> dict[str, Any]:
    t_price = yf.Ticker(asset.ticker)
    h = t_price.history(period="5d")
    price = _safe_float(h["Close"].iloc[-1]) if getattr(h, "empty", True) is False else None

    valuation_ticker = asset.valuation_ticker or asset.ticker
    v_info = yf.Ticker(valuation_ticker).info or {}
    pe = _safe_float(v_info.get("trailingPE"))
    if pe is not None and pe <= 0:
        pe = None

    fair = asset.benchmark_fair_pe or 20.0
    ratio = (pe / fair) if pe is not None and fair > 0 else None
    fair_price = (price / ratio) if ratio is not None and price not in (None, 0) else None
    valuation_gap_pct = ((fair_price / price) - 1.0) * 100.0 if fair_price is not None and price not in (None, 0) else None
    assessment = _valuation_label(ratio, "broad_market")

    return {
        "name": asset.name,
        "ticker": asset.ticker,
        "index": asset.index_name,
        "benchmark": True,
        "latest_period": "",
        "prior_period": "",
        "sector": "Broad Market Index",
        "industry": "Diversified",
        "price": round(price, 2) if price is not None else None,
        "valuation_model": "PE",
        "valuation_style": "broad_market",
        "actual_multiple": round(pe, 2) if pe is not None else None,
        "fair_multiple": round(fair, 2),
        "multiple_ratio": round(ratio, 2) if ratio is not None else None,
        "fair_price": round(fair_price, 2) if fair_price is not None else None,
        "valuation_gap_pct": round(valuation_gap_pct, 1) if valuation_gap_pct is not None else None,
        "assessment": assessment,
        "opportunity_score": 0.0,
        "score_total": None,
        "grade": "N/A",
        "data_completeness_pct": None,
        "components": {},
        "metrics": {},
    }


def build_snapshot(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build full snapshot for all assets."""
    selected_assets = _resolve_assets(settings)
    assets: list[dict[str, Any]] = []
    for asset in selected_assets:
        try:
            row = _compute_benchmark(asset) if asset.benchmark else _compute_company(asset)
        except Exception as err:  # noqa: BLE001
            row = {
                "name": asset.name,
                "ticker": asset.ticker,
                "index": asset.index_name,
                "benchmark": asset.benchmark,
                "price": None,
                "assessment": "N/A",
                "error": str(err),
                "components": {},
                "metrics": {},
                "score_total": None,
                "grade": "N/A",
                "opportunity_score": -999.0,
            }
        assets.append(row)

    ranked = sorted(
        [a for a in assets if not a.get("benchmark", False)],
        key=lambda item: (item.get("opportunity_score", -999.0), item.get("score_total") or 0.0),
        reverse=True,
    )
    top = ranked[:10]
    upcoming = sorted(
        [
            {
                "company": a.get("name"),
                "ticker": a.get("ticker"),
                "index": a.get("index"),
                "next_earnings_iso": a.get("next_earnings_iso"),
                "next_earnings_ts": a.get("next_earnings_ts"),
                "assessment": a.get("assessment"),
                "price": a.get("price"),
                "fair_price": a.get("fair_price"),
                "score_total": a.get("score_total"),
                "grade": a.get("grade"),
                "opportunity_score": a.get("opportunity_score"),
                "valuation_model": a.get("valuation_model"),
                "multiple_ratio": a.get("multiple_ratio"),
                "components": a.get("components", {}),
                "metrics": a.get("metrics", {}),
            }
            for a in assets
            if not a.get("benchmark", False) and a.get("next_earnings_ts") is not None
        ],
        key=lambda item: item.get("next_earnings_ts") or 0,
    )
    next_5 = upcoming[:5]
    summary = {
        "undervalued": sum(1 for a in assets if a.get("assessment") == "Undervalued"),
        "fair": sum(1 for a in assets if a.get("assessment") == "Fair"),
        "overvalued": sum(1 for a in assets if a.get("assessment") == "Overvalued"),
        "na": sum(1 for a in assets if a.get("assessment") == "N/A"),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "settings": {
            "list_mode": str((settings or {}).get("list_mode", "default")),
            "custom_tickers": str((settings or {}).get("custom_tickers", "")),
            "include_benchmarks": bool((settings or {}).get("include_benchmarks", True)),
        },
        "assets": assets,
        "top_opportunities": top,
        "upcoming_earnings_next_5": next_5,
        "summary": summary,
    }
