#!/usr/bin/env python3
"""Download ECB monthly average USD/EUR reference rates and write seeds/seed_fx_rates.csv.

Series: ECB EXR  M.USD.EUR.SP00.A  (monthly average, USD per 1 EUR).
Output column eur_per_usd = 1 / (USD per EUR), i.e. how many euros one dollar buys.

Usage:
    python scripts/load_fx.py                 # from 2019-01 to today
    python scripts/load_fx.py --start 2019-01 --out seeds/seed_fx_rates.csv

Then load it into BigQuery (US location):
    bq load --location=US --source_format=CSV --skip_leading_rows=1 --replace \
        unit_econ.seed_fx_rates seeds/seed_fx_rates.csv month:DATE,eur_per_usd:FLOAT64,source:STRING

If the ECB changes the endpoint, check the series key in the ECB Data Portal (data.ecb.europa.eu).
"""
import argparse
import csv
import io
import os
import sys
import urllib.request

URL = ("https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A"
       "?format=csvdata&startPeriod={start}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01", help="first month, YYYY-MM")
    ap.add_argument("--out", default="seeds/seed_fx_rates.csv")
    args = ap.parse_args()

    with urllib.request.urlopen(URL.format(start=args.start), timeout=60) as r:
        text = r.read().decode("utf-8")

    rows = []
    for rec in csv.DictReader(io.StringIO(text)):
        period, value = rec.get("TIME_PERIOD"), rec.get("OBS_VALUE")
        if not period or not value:
            continue
        usd_per_eur = float(value)
        rows.append((f"{period}-01", round(1.0 / usd_per_eur, 6), "ECB_EXR_M_USD_EUR_SP00_A"))

    if not rows:
        print("No rows parsed - check the endpoint / series key.", file=sys.stderr)
        return 1

    rows.sort()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "eur_per_usd", "source"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} months ({rows[0][0]} .. {rows[-1][0]}) to {args.out}")
    print("Months after the last published ECB month are forward-filled in sql/02_seed_fx.sql.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
