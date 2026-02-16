# homeassistant Investing Score Card

Home Assistant HACS integration for weekly investment ranking and valuation:
- 20 companies (S&P 500 + OMXC25)
- 3 index benchmarks (`ACWI`, `S&P 500`, `OMXC25`)
- Sector-aware fair value model (tech/software allowed higher PE)
- Ranking with top opportunities shown first

## Screenshots

![Dashboard Preview](docs/screenshots/dashboard-modern.svg)
![Asset Detail Preview](docs/screenshots/asset-detail-modern.svg)

## Data Model

Each asset includes:
- `score_total` and `grade` (`A+` to `F`)
- component scoring:
  - growth (`revenue_yoy`, `eps_yoy`)
  - profitability (`op_margin_level`, `op_margin_yoy`)
  - guidance (default `unchanged` weight)
  - capital strength (`fcf_yoy`, `net_debt_to_ebitda`)
- valuation:
  - current price
  - fair multiple + fair price
  - `Undervalued` / `Fair` / `Overvalued`

## Home Assistant Entities

- `sensor.<name>_top_opportunities`
  - state: top-ranked asset
  - attributes: sorted `top_10` list with full details
- `sensor.<name>_market_summary`
  - counts for undervalued/fair/overvalued
- one sensor per asset
  - state: valuation assessment
  - attributes: score breakdown, metrics, fair price, valuation gap

## Weekly Updates

Built-in coordinator refresh interval: **7 days**.

Optional automation (recommended) to force refresh every Monday:

```yaml
alias: Investing Score Weekly Refresh
trigger:
  - platform: time
    at: "07:00:00"
condition:
  - condition: time
    weekday:
      - mon
action:
  - service: investing_score_card.refresh_data
mode: single
```

## HA Native Styling

This integration is built to follow Home Assistant native UX (no custom applet UI).

- Example Lovelace view:
  - `docs/lovelace/dashboard.yaml`
- Optional soft native theme:
  - `docs/lovelace/theme_soft_native.yaml`

Style goals:
- rounded cards and buttons (`ha-card-border-radius`)
- light separators and borders
- clean tile/button layout (native cards only)

## Manual Script

Generate a snapshot JSON outside HA:

```bash
python3 scripts/update_weekly_snapshot.py --output data/weekly_snapshot.json
```

## Install

1. In HACS, add custom repository:
   - `https://github.com/nikolajflojgaard/homeassistant-investing-score-card`
   - category: `Integration`
2. Install integration and restart Home Assistant.
3. Add `homeassistant Investing Score Card` from Settings -> Devices & Services.
