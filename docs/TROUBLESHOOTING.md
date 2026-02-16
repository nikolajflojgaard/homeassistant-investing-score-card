# Troubleshooting

## Integration Won't Load

- Check Home Assistant logs for `custom_components.investing_score_card`.
- Ensure the integration domain folder exists: `custom_components/investing_score_card/`.

## Config Flow Missing

- Confirm `manifest.json` has `"config_flow": true`.
- Confirm `config_flow.py` exists and class name matches `<Name>ConfigFlow`.

## Reauth Loop

- If you configured a `host`, make sure you also set an `api_key` (this template enforces that in `api.py`).
- Inspect diagnostics output (Settings -> Devices & Services -> ... -> Download diagnostics).

