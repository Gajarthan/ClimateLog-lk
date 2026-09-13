"""Sri Lanka report map using explicit historical station reference matches."""

import json
from importlib.resources import files
from pathlib import Path


def map_points(rows):
    catalog = json.loads(
        files("weather_lk.stations")
        .joinpath("data/map_stations.json")
        .read_text(encoding="utf-8")
    )["stations"]
    return [
        dict(row, **catalog[row["station_id"]])
        for row in rows
        if row["station_id"] in catalog
    ]


def render_map(snapshot, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Patch
    from matplotlib.ticker import MultipleLocator

    points = map_points(snapshot["observations"])
    boundary = json.loads(
        files("weather_lk.stations")
        .joinpath("data/sri_lanka.geojson")
        .read_text(encoding="utf-8")
    )["geometry"]
    polygons = (
        boundary["coordinates"]
        if boundary["type"] == "MultiPolygon"
        else [boundary["coordinates"]]
    )
    colors = ["#e4edf5", "#a9c4ee", "#9be3d3", "#43b6a0", "#157d74", "#405164"]

    def color(row):
        if row.get("rain") is None:
            return colors[5]
        if row.get("trace_rain"):
            return colors[1]
        return colors[
            0
            if row["rain"] == 0
            else 2
            if row["rain"] <= 5
            else 3
            if row["rain"] <= 15
            else 4
        ]

    fig, ax = plt.subplots(figsize=(12, 11))
    try:
        fig.set_facecolor("#0d1723")
        ax.set_facecolor("#0d1723")
        for polygon in polygons:
            ax.add_patch(
                Polygon(
                    polygon[0],
                    closed=True,
                    facecolor="#193346",
                    edgecolor="#608a9a",
                    linewidth=1.2,
                    zorder=1,
                )
            )
            for hole in polygon[1:]:
                ax.add_patch(
                    Polygon(
                        hole,
                        closed=True,
                        facecolor="#0d1723",
                        edgecolor="none",
                        zorder=1,
                    )
                )
        ax.set_xlim(78.7, 82.95)
        ax.set_ylim(5.6, 10.05)
        ax.set_aspect(1.01)
        ax.xaxis.set_major_locator(MultipleLocator(1))
        ax.yaxis.set_major_locator(MultipleLocator(1))
        ax.grid(color="#263849", linewidth=0.6, linestyle=":", zorder=0)
        ax.tick_params(colors="#90a9bb", length=0, labelsize=10)
        ax.set_xlabel("Longitude (°E)", color="#90a9bb")
        ax.set_ylabel("Latitude (°N)", color="#90a9bb")
        for spine in ax.spines.values():
            spine.set_visible(False)
        for side in ("left", "right"):
            group = sorted(
                [
                    p
                    for p in points
                    if ("left" if p["longitude"] < 80.6 else "right") == side
                ],
                key=lambda p: p["latitude"],
            )
            previous = 5.65
            for p in group:
                y = max(p["latitude"], previous + 0.31)
                previous = y
                x = 78.92 if side == "left" else 82.72
                align = "left" if side == "left" else "right"
                ax.plot(
                    [p["longitude"], x],
                    [p["latitude"], y],
                    color="#668396",
                    linewidth=0.65,
                    zorder=2,
                )
                ax.scatter(
                    p["longitude"],
                    p["latitude"],
                    s=110,
                    c=color(p),
                    edgecolors="#ffffff",
                    linewidth=0.75,
                    zorder=4,
                )
                ax.text(
                    x,
                    y + 0.06,
                    p["place"],
                    ha=align,
                    va="bottom",
                    color="#f0f6fc",
                    fontsize=11.5,
                    fontweight="bold",
                    zorder=5,
                    bbox=dict(facecolor="#0d1723", edgecolor="none", pad=2),
                )
                rain = (
                    "Missing"
                    if p.get("rain") is None
                    else ("Trace" if p.get("trace_rain") else f"{p['rain']:.1f} mm")
                )
                maximum = "—" if p.get("max_temp") is None else f"{p['max_temp']:.1f}°C"
                ax.text(
                    x,
                    y - 0.015,
                    f"{rain}  /  max {maximum}",
                    ha=align,
                    va="top",
                    color="#acccdf",
                    fontsize=10,
                    zorder=5,
                    bbox=dict(facecolor="#0d1723", edgecolor="none", pad=2),
                )
        ax.annotate(
            "N",
            xy=(82.7, 9.85),
            xytext=(82.7, 9.53),
            ha="center",
            color="#e6edf3",
            fontsize=14,
            arrowprops=dict(arrowstyle="-|>", color="#e6edf3", lw=1.3),
        )
        fig.suptitle(
            f"Sri Lanka | {snapshot['report_date']}",
            x=0.10,
            y=0.98,
            ha="left",
            color="#f4f8fc",
            fontsize=23,
            fontweight="bold",
        )
        fig.text(
            0.10,
            0.945,
            f"Rainfall and daily maximum temperature · {len(points)} of {len(snapshot['observations'])} stations mapped",
            color="#aebfd0",
            fontsize=12,
        )
        ax.legend(
            handles=[
                Patch(facecolor=c, label=l)
                for c, l in zip(
                    colors,
                    ["0 mm", "Trace", ">0–5 mm", ">5–15 mm", ">15 mm", "Missing"],
                )
            ],
            loc="lower center",
            bbox_to_anchor=(0.5, -0.13),
            ncol=6,
            frameon=False,
            labelcolor="#cbd9e6",
            fontsize=10,
        )
        fig.text(
            0.5,
            0.035,
            "Historical reference positions; current instrument locations are not independently verified.",
            ha="center",
            color="#aebfd0",
            fontsize=10,
        )
        fig.text(
            0.5,
            0.015,
            "Boundary: Natural Earth · Locations: NOAA NCEI ISD · Weather: Department of Meteorology",
            ha="center",
            color="#90a9bb",
            fontsize=9,
        )
        fig.subplots_adjust(left=0.07, right=0.97, top=0.91, bottom=0.16)
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        path = output / "sri-lanka-map.png"
        fig.savefig(path, dpi=160, facecolor=fig.get_facecolor())
        return path
    finally:
        plt.close(fig)
