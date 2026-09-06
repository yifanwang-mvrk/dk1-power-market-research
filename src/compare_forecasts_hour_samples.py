"""Compare saved Forecasts_Hour day samples without fetching new data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


KEY_COLUMNS = ["HourUTC", "PriceArea", "ForecastType"]


def summarize(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not records:
        return {
            "file": path.name,
            "records": 0,
            "delivery_hours": 0,
            "duplicate_key_rows": 0,
            "solar_5h_zero": None,
            "solar_1h_zero": None,
            "solar_5h_or_1h_zero": None,
            "solar_zero_hours_dk": [],
        }

    frame = pd.DataFrame(records)
    solar = frame[frame["ForecastType"].eq("Solar")].copy()
    zero_mask = solar["Forecast5Hour"].eq(0) | solar["Forecast1Hour"].eq(0)
    return {
        "file": path.name,
        "records": int(len(frame)),
        "delivery_hours": int(frame["HourUTC"].nunique()),
        "duplicate_key_rows": int(frame.duplicated(KEY_COLUMNS, keep=False).sum()),
        "solar_5h_zero": int(solar["Forecast5Hour"].eq(0).sum()),
        "solar_1h_zero": int(solar["Forecast1Hour"].eq(0).sum()),
        "solar_5h_or_1h_zero": int(zero_mask.sum()),
        "solar_zero_hours_dk": [value[11:16] for value in solar.loc[zero_mask, "HourDK"]],
    }


def render_markdown(rows: list[dict[str, object]]) -> str:
    lines = [
        "# Forecasts_Hour Seasonal and Known-Gap Sample Facts",
        "",
        "All samples are restricted to DK1 and dates inside the development period.",
        "The known-gap sample tests the official missing-data notice.",
        "",
        "| Sample | Records | Hours | Duplicate key rows | Solar 5h zero | Solar 1h zero | Either zero |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        values = [row["solar_5h_zero"], row["solar_1h_zero"], row["solar_5h_or_1h_zero"]]
        formatted = ["n/a" if value is None else str(value) for value in values]
        lines.append(
            f"| {row['file']} | {row['records']} | {row['delivery_hours']} | "
            f"{row['duplicate_key_rows']} | {formatted[0]} | {formatted[1]} | {formatted[2]} |"
        )
    lines.extend(["", "## Solar zero-pair hours in Danish local time", ""])
    for row in rows:
        hours = ", ".join(row["solar_zero_hours_dk"]) or "none"
        lines.append(f"- `{row['file']}`: {hours}")
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "These observations do not determine whether a zero is a valid zero forecast or an unavailable forecast encoded as zero.",
            "No point-in-time eligibility decision is made by this report.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()

    rows = [summarize(path) for path in args.inputs]
    result = {
        "samples": rows,
        "interpretation_boundary": [
            "Zero is not automatically missing.",
            "Zero is not automatically a validated forecast.",
            "This report does not establish point-in-time eligibility.",
        ],
    }
    args.json_output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(rows), encoding="utf-8")


if __name__ == "__main__":
    main()
