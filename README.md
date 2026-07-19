# Value Screener – Three‑Pillar Commodity Cycle Investing

This screener implements Andy Hoese’s process:
1. **Macro**: Only act when commodities are historically cheap vs stocks & gold.
2. **Sector**: Focus on “hated” sectors (well below 5‑ and 10‑year highs).
3. **Stock**: Apply cost, debt, dilution, and value filters.
4. **Technical**: Wait for SMA cross and volume confirmation.

All data is cached in `data/screener.db` to minimise API calls and disk usage.

## Usage

```bash
pip install -r requirements.txt
python scripts/run_screener.py
