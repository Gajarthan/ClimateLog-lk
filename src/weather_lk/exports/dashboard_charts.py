"""Render station comparison charts for the README snapshot."""


def render_station_charts(snapshot, asset):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = snapshot["observations"]
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "text.color": "#e6edf3",
            "axes.labelcolor": "#aebfd0",
            "xtick.color": "#aebfd0",
            "ytick.color": "#e6edf3",
            "axes.edgecolor": "#283a4b",
            "savefig.facecolor": "#0d1723",
            "figure.facecolor": "#0d1723",
            "axes.facecolor": "#0d1723",
        }
    )

    def figure(height):
        fig, ax = plt.subplots(figsize=(12, height), layout="constrained")
        for edge in ax.spines.values():
            edge.set_visible(False)
        ax.grid(axis="x", color="#283a4b", alpha=0.6)
        ax.set_axisbelow(True)
        return fig, ax

    rain = sorted(
        [r for r in rows if r["rain"] is not None],
        key=lambda r: r["rain"],
        reverse=True,
    )[:10][::-1]
    fig, ax = figure(5.6)
    ax.barh(
        [r["place"] for r in rain],
        [r["rain"] for r in rain],
        color="#3ddbb2",
        height=0.6,
    )
    for i, r in enumerate(rain):
        ax.text(r["rain"] + 0.4, i, f"{r['rain']:.1f}", va="center")
    ax.set_xlim(0, max(1, max(r["rain"] for r in rain) * 1.18))
    ax.set_xlabel("Reported rainfall (mm)")
    ax.set_title(
        "Rainfall leaders | " + snapshot["report_date"],
        loc="left",
        fontsize=17,
        pad=20,
        color="#ffffff",
    )
    fig.savefig(asset / "rainfall.png", dpi=150)
    plt.close(fig)
    paired = sorted(
        [r for r in rows if r["min_temp"] is not None and r["max_temp"] is not None],
        key=lambda r: r["max_temp"],
    )
    fig, ax = figure(8.4)
    for i, r in enumerate(paired):
        ax.plot(
            [r["min_temp"], r["max_temp"]],
            [i, i],
            color="#35546d",
            linewidth=4,
            zorder=1,
        )
    ax.scatter(
        [r["min_temp"] for r in paired],
        range(len(paired)),
        color="#72b8ff",
        s=40,
        label="Minimum",
        zorder=2,
    )
    ax.scatter(
        [r["max_temp"] for r in paired],
        range(len(paired)),
        color="#ffbf69",
        s=40,
        label="Maximum",
        zorder=2,
    )
    ax.set_yticks(range(len(paired)), [r["place"] for r in paired])
    ax.set_xlabel("Temperature (°C)")
    ax.set_title(
        "Daily temperature ranges | " + snapshot["report_date"],
        loc="left",
        fontsize=17,
        pad=20,
        color="#ffffff",
    )
    ax.legend(loc="lower right", facecolor="#162635", edgecolor="none")
    fig.savefig(asset / "temperature.png", dpi=150)
    plt.close(fig)
