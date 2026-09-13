<div align="center">

# ClimateLog LK

### Sri Lanka · Weather observation dashboard

**[Weather snapshot](#weather-snapshot) · [Data quality](#data-quality) · [Station readings](#station-readings) · [Source data](#source-data)**

</div>

---

## Weather snapshot

**Report: $report_date · Period ending 08:30 SLST**

Captured $captured from the Department of Meteorology.

> This is a published snapshot, not a live feed. The date above identifies the data shown. Values are accurate to the report date shown.

![Weather overview for $report_date: $count station readings](docs/dashboard/overview.svg)

[Download observations](docs/dashboard/snapshot.json) · [View archived source PDF](docs/dashboard/report.pdf) · [Official source](https://meteo.gov.lk/)

### Rainfall

![Top ten stations by reported rainfall](docs/dashboard/rainfall.png)

Station measurements in millimetres. These values are not a regional rainfall total.

<details>
<summary><strong>Explore the rainfall heatmap / all $count stations</strong></summary>

![Rainfall heatmap showing all $count stations in alphabetical order](docs/dashboard/station-rainfall.png)

Each tile is a station, arranged alphabetically. This is not a geographic map. Color bands distinguish zero, trace, and measured rainfall; exact millimetres are printed on every tile.

</details>

### Temperature

![Daily minimum and maximum temperatures by station](docs/dashboard/temperature.png)

Each line connects one station's daily minimum and maximum. Only stations with both readings are shown.

## Data quality

![Measurement availability: rainfall $rain_count of $count, paired temperatures $paired_count of $count](docs/dashboard/coverage.png)

$quality_table

**$trace_count trace-rain readings** · **$unknown_count unresolved station identities** · **$coordinate_count rows with unverified historical coordinates**

Missing readings are shown as **—**. Zero is a measured value; **Trace** is retained separately. Coverage describes this report, not the entire national station network. Station and coordinate flags remain available in the observation download. No location map is shown because coordinate verification is incomplete.

## Station readings

<details>
<summary><strong>Open all $count station readings</strong></summary>

$station_table

</details>

## Source data

[Download station observations](docs/dashboard/snapshot.json) · [Read the original weather report](docs/dashboard/report.pdf) · [Department of Meteorology](https://meteo.gov.lk/)

---

ClimateLog LK · Sri Lankan rainfall and temperature observations. Measurements use millimetres and degrees Celsius. [MIT license](LICENSE).
