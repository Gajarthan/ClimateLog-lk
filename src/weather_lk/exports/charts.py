"""Render explicit figures lazily, with gaps retained on a calendar axis."""

from datetime import date, timedelta

from weather_lk.analytics.statistics import summarize


def render_charts(rows, output_dir):
    if not rows:
        return []
    # Heavy optional imports occur only for a requested nonempty chart export.
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib import pyplot as plt
    from matplotlib.dates import DateFormatter, DayLocator

    output_dir.mkdir(parents=True, exist_ok=True)
    end = max(date.fromisoformat(row["date"]) for row in rows)
    start = max(
        min(date.fromisoformat(row["date"]) for row in rows), end - timedelta(days=89)
    )
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    by_date = {}
    for row in rows:
        by_date.setdefault(row["date"], []).append(row)
    stats = [summarize(by_date.get(day.isoformat(), [])) for day in dates]
    paths = []
    for kind in ("temperature", "rainfall", "min_max_plot"):
        figure = Figure(figsize=(10, 4.5), layout="constrained")
        try:
            FigureCanvasAgg(figure)
            axis = figure.subplots()
            if kind == "temperature":
                for key, label, color in [
                    ("min_temp", "Mean daily minimum", "#2274a5"),
                    ("max_temp", "Mean daily maximum", "#d1495b"),
                ]:
                    axis.plot(
                        dates,
                        [
                            s[key]["mean"]
                            if s[key]["mean"] is not None
                            else float("nan")
                            for s in stats
                        ],
                        label=label,
                        color=color,
                    )
                axis.set_ylabel("Temperature (°C)")
                axis.legend()
            elif kind == "rainfall":
                axis.bar(
                    dates,
                    [
                        s["rain"]["mean"]
                        if s["rain"]["mean"] is not None
                        else float("nan")
                        for s in stats
                    ],
                    color="#2274a5",
                )
                axis.set_ylabel("Mean reported rainfall (mm)")
            else:
                paired = [
                    row
                    for row in rows
                    if row.get("min_temp") is not None
                    and row.get("max_temp") is not None
                    and start.isoformat() <= row["date"] <= end.isoformat()
                ]
                axis.scatter(
                    [row["min_temp"] for row in paired],
                    [row["max_temp"] for row in paired],
                    alpha=0.5,
                    color="#2274a5",
                )
                axis.set_xlabel("Daily minimum (°C)")
                axis.set_ylabel("Daily maximum (°C)")
                if not paired:
                    axis.text(
                        0.5,
                        0.5,
                        "No paired temperature observations",
                        ha="center",
                        transform=axis.transAxes,
                    )
            axis.set_title(f"{kind.replace('_', ' ').title()} · {start} to {end}")
            axis.grid(alpha=0.2)
            if kind != "min_max_plot":
                axis.xaxis.set_major_locator(
                    DayLocator(interval=max(1, len(dates) // 8))
                )
                axis.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
                figure.autofmt_xdate()
            path = output_dir / f"{kind}.png"
            figure.savefig(path, dpi=140)
            paths.append(path)
        finally:
            plt.close(figure)
            figure.clear()
    return paths
