"""Render README visual assets from the committed, dated weather snapshot."""

import json
import math
import textwrap
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "dashboard"


def render(assets=ASSETS):
    snapshot = json.loads((assets / "snapshot.json").read_text(encoding="utf-8"))
    rows = snapshot["observations"]
    day = snapshot["report_date"]
    high_rain = max((r for r in rows if r["rain"] is not None), key=lambda r: r["rain"])
    high_temp = max(
        (r for r in rows if r["max_temp"] is not None), key=lambda r: r["max_temp"]
    )
    low_temp = min(
        (r for r in rows if r["min_temp"] is not None), key=lambda r: r["min_temp"]
    )
    cards = [
        (
            "STATION READINGS",
            str(len(rows)),
            "in the published report",
            "#b9adff",
            "stations",
        ),
        (
            "HIGHEST RAINFALL",
            f"{high_rain['rain']:.1f}",
            f"mm / {high_rain['place']}",
            "#50dec0",
            "rain",
        ),
        (
            "HIGHEST MAXIMUM",
            f"{high_temp['max_temp']:.1f}",
            f"°C / {high_temp['place']}",
            "#ffc477",
            "hot",
        ),
        (
            "LOWEST MINIMUM",
            f"{low_temp['min_temp']:.1f}",
            f"°C / {low_temp['place']}",
            "#84c2ff",
            "cool",
        ),
    ]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="466" viewBox="0 0 1000 466" role="img" aria-labelledby="title desc">',
        '<title id="title">ClimateLog LK report overview</title>',
        f'<desc id="desc">Report {day}. {len(rows)} stations. Highest rainfall {high_rain["rain"]} millimetres at {escape(high_rain["place"])}. Highest maximum {high_temp["max_temp"]} degrees Celsius at {escape(high_temp["place"])}. Lowest minimum {low_temp["min_temp"]} degrees Celsius at {escape(low_temp["place"])}.</desc>',
        '<rect width="1000" height="466" rx="20" fill="#0d1723"/>',
        '<g font-family="Segoe UI,DejaVu Sans,sans-serif">',
        '<text x="28" y="40" font-size="18" font-weight="700" fill="#e6edf3">DAILY OBSERVATION BOARD</text>',
        f'<text x="972" y="40" text-anchor="end" font-size="15" fill="#aebfd0">{day} · 08:30 SLST</text>',
    ]
    for index, (label, value, detail, accent, icon) in enumerate(cards):
        x = 24 + (index % 2) * 488
        y = 64 + (index // 2) * 188
        svg += [
            f'<rect x="{x}" y="{y}" width="464" height="168" rx="12" fill="#142437" stroke="#283d53"/>',
            f'<rect x="{x}" y="{y + 24}" width="4" height="120" rx="2" fill="{accent}"/>',
            f'<text x="{x + 24}" y="{y + 34}" font-size="14" letter-spacing="1.3" fill="{accent}">{label}</text>',
            f'<text x="{x + 24}" y="{y + 102}" font-size="58" font-weight="700" fill="#f4f8fc">{value}</text>',
            f'<text x="{x + 26}" y="{y + 139}" font-size="17" fill="#bbccdc">{escape(detail)}</text>',
        ]
        for j in range(5):
            svg.append(
                f'<line x1="{x + 410}" x2="{x + 430}" y1="{y + 57 + j * 14}" y2="{y + 57 + j * 14}" stroke="#33516c" stroke-width="2"/>'
            )
    svg += ["</g></svg>"]
    (assets / "overview.svg").write_text("\n".join(svg) + "\n", encoding="utf-8")

    colors = ["#e4edf5", "#a9c4ee", "#9be3d3", "#43b6a0", "#157d74", "#405164"]

    def category(row):
        if row["rain"] is None:
            return 5
        if row["trace_rain"]:
            return 1
        if row["rain"] == 0:
            return 0
        if row["rain"] <= 5:
            return 2
        if row["rain"] <= 15:
            return 3
        return 4

    fig, ax = plt.subplots(figsize=(15, 10.5), layout="constrained")
    fig.set_facecolor("#0d1723")
    ax.set_facecolor("#0d1723")
    ordered = sorted(rows, key=lambda r: r["place"])
    columns = 6
    height = math.ceil(len(ordered) / columns)
    for i, row in enumerate(ordered):
        x, y = i % columns, height - 1 - i // columns
        kind = category(row)
        ax.add_patch(
            FancyBboxPatch(
                (x + 0.035, y + 0.035),
                0.93,
                0.90,
                boxstyle="round,pad=0.006,rounding_size=0.04",
                facecolor=colors[kind],
                edgecolor="none",
            )
        )
        ink = "#f4f8fc" if kind in (4, 5) else "#10283a"
        name = "\n".join(textwrap.wrap(row["place"], width=19))
        ax.text(
            x + 0.5, y + 0.66, name, ha="center", va="center", fontsize=9.5, color=ink
        )
        value = (
            "—"
            if row["rain"] is None
            else ("Trace" if row["trace_rain"] else f"{row['rain']:.1f}")
        )
        ax.text(
            x + 0.5,
            y + 0.26,
            value,
            ha="center",
            va="center",
            fontsize=17,
            fontweight="bold",
            color=ink,
        )
    ax.set_xlim(0, columns)
    ax.set_ylim(-0.45, height + 0.10)
    ax.axis("off")
    ax.set_title(
        f"Rainfall across {len(rows)} stations | {day}",
        loc="left",
        fontsize=20,
        pad=24,
        color="#f4f8fc",
    )
    ax.legend(
        handles=[
            Patch(facecolor=c, label=l)
            for c, l in zip(
                colors, ["0 mm", "Trace", ">0–5 mm", ">5–15 mm", ">15 mm", "Missing"]
            )
        ],
        loc="lower center",
        ncol=6,
        frameon=False,
        labelcolor="#cbd9e6",
        fontsize=11,
    )
    fig.savefig(assets / "station-rainfall.png", dpi=140, facecolor=fig.get_facecolor())
    plt.close(fig)

    available = [
        sum(r["rain"] is not None for r in rows),
        sum(r["min_temp"] is not None and r["max_temp"] is not None for r in rows),
    ]
    labels = ["Rainfall", "Paired temperatures"]
    fig, ax = plt.subplots(figsize=(12, 2.5), layout="constrained")
    fig.set_facecolor("#0d1723")
    ax.set_facecolor("#0d1723")
    for i, (label, value) in enumerate(zip(labels, available)):
        y = 1 - i
        ax.barh(y, len(rows), height=0.38, color="#273d51")
        ax.barh(y, value, height=0.38, color=["#50dec0", "#84c2ff"][i])
        ax.text(-2, y, label, ha="right", va="center", color="#e6edf3", fontsize=13)
        ax.text(
            len(rows) + 2,
            y,
            f"{value}/{len(rows)}  ·  {value / len(rows):.0%}",
            ha="left",
            va="center",
            color="#e6edf3",
            fontsize=13,
        )
    ax.set_xlim(-24, len(rows) + 21)
    ax.set_ylim(-0.5, 1.6)
    ax.axis("off")
    ax.set_title(
        "Measurement availability", loc="left", color="#f4f8fc", fontsize=17, pad=12
    )
    fig.savefig(assets / "coverage.png", dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    render()
