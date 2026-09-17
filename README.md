<div align="center">

# ClimateLog LK

### Sri Lanka · Weather observation dashboard

**[Weather snapshot](#weather-snapshot) · [Sri Lanka map](#sri-lanka-map) · [Data quality](#data-quality) · [Station readings](#station-readings) · [Source data](#source-data)**

</div>

---

## Weather snapshot

**Report: 2026-09-17 · Period ending 08:30 SLST**

Captured 17 Sep 2026 · 15:04 SLST from the Department of Meteorology.

> This is a published snapshot, not a live feed. The date above identifies the data shown. Values are accurate to the report date shown.

![Weather overview for 2026-09-17: 60 station readings](docs/dashboard/overview.svg)

[Download observations](docs/dashboard/snapshot.json) · [View archived source PDF](docs/dashboard/report.pdf) · [Official source](https://meteo.gov.lk/)

## Sri Lanka map

![Sri Lanka station map with rainfall and daily maximum temperatures for 2026-09-17](docs/dashboard/sri-lanka-map.png)

Markers show stations matched to published historical coordinates. Unmatched locations are omitted, not estimated. The map labels rainfall and maximum temperature; all 60 readings remain available below. [Map sources and location notes](docs/dashboard/MAP_SOURCES.md).

### Rainfall

![Top ten stations by reported rainfall](docs/dashboard/rainfall.png)

Station measurements in millimetres. These values are not a regional rainfall total.

<details>
<summary><strong>Explore the rainfall heatmap / all 60 stations</strong></summary>

![Rainfall heatmap showing all 60 stations in alphabetical order](docs/dashboard/station-rainfall.png)

Each tile is a station, arranged alphabetically. This is not a geographic map. Color bands distinguish zero, trace, and measured rainfall; exact millimetres are printed on every tile.

</details>

### Temperature

![Daily minimum and maximum temperatures by station](docs/dashboard/temperature.png)

Each line connects one station's daily minimum and maximum. Only stations with both readings are shown.

## Data quality

![Measurement availability: rainfall 60 of 60, paired temperatures 24 of 60](docs/dashboard/coverage.png)

| Measure | Available | Missing |
| --- | ---: | ---: |
| Rainfall | 60 / 60 | 0 |
| Minimum temperature | 24 / 60 | 36 |
| Maximum temperature | 24 / 60 | 36 |
| Paired temperatures | 24 / 60 | 36 |

**2 trace-rain readings** · **16 unresolved station identities** · **41 rows with unverified historical coordinates**

Missing readings are shown as **—**. Zero is a measured value; **Trace** is retained separately. Coverage describes this report, not the entire national station network. Station and coordinate flags remain available in the observation download. The map uses a separate published reference catalog; its historical positions do not verify current instrument locations.

## Station readings

<details>
<summary><strong>Open all 60 station readings</strong></summary>

| Station | Rain (mm) | Minimum (°C) | Maximum (°C) |
| --- | ---: | ---: | ---: |
| . Dellawa TF (ARG) | 47.0 | — | — |
| . Devagiri TF (ARG) | 62.5 | — | — |
| . Devidson TF (ARG) | 50.0 | — | — |
| . Ivy Hills TF (ARG) | 87.0 | — | — |
| . Menikkanda TF (ARG) | 85.0 | — | — |
| Anuradhapura | 0.0 | 25.9 | 34.4 |
| Baddegama | 61.4 | — | — |
| Badulla | 0.2 | 20.9 | 30.1 |
| Bandarawela | 20.5 | 19.3 | 26.1 |
| Batticaloa | 0.0 | 25.6 | 32.8 |
| Batuwangala | 40.4 | — | — |
| Benthotawatta | 117.4 | — | — |
| Boossa (ARG) | 55.0 | — | — |
| Bowatenna | 0.0 | — | — |
| Canyon | 0.7 | — | — |
| Castlereigh | 1.0 | — | — |
| Colombo | 0.6 | 26.0 | 31.2 |
| Dunumale Estate (ARG) | 72.5 | — | — |
| Ellakanda Watta (ARG) | 75.0 | — | — |
| Galle | 45.1 | 24.1 | 28.0 |
| Hambantota | 0.6 | 25.1 | 30.5 |
| Inginiyagala | 0.0 | — | — |
| Jaffna | 0.0 | 28.4 | 33.7 |
| Kadduwa (ARG) | 42.5 | — | — |
| Katugastota | 0.3 | 22.6 | 30.3 |
| Katunayake | 3.3 | 25.0 | 31.0 |
| Keselhenawa (ARG) | 55.5 | — | — |
| Kethendola | 48.2 | — | — |
| Kotmale | 0.0 | — | — |
| Kukuleganaga | 5.0 | — | — |
| Kurunegala | Trace | 25.6 | 32.6 |
| Laxapana | 3.8 | — | — |
| Maha Illuppallama | 0.0 | 25.1 | 33.8 |
| Mannar | Trace | 28.3 | 31.9 |
| Maskeliya (DOM) | 0.0 | — | — |
| Mattala | 1.3 | 24.6 | 31.5 |
| Maussakele | 0.0 | — | — |
| Moneragala | 2.9 | 24.2 | 32.6 |
| Monrovia | 65.8 | — | — |
| Mullaitivu | 1.4 | 27.0 | 35.1 |
| Norton | 3.4 | — | — |
| Nuwara Eliya | 4.3 | 15.5 | 20.6 |
| Poddiwela Farm | 40.6 | — | — |
| Polonnaruwa | 0.0 | 25.0 | 35.4 |
| Pottuvil | 0.6 | 26.0 | 33.1 |
| Puttalam | 0.0 | 27.4 | 32.4 |
| Randenigala | 0.0 | — | — |
| Rantambe | 0.0 | — | — |
| Ratmalana | 2.1 | 25.9 | 31.7 |
| Ratnapura | 25.6 | 24.7 | 30.5 |
| Samanala Wawa | 0.0 | — | — |
| Sirikandura Estate (ARG) | 61.0 | — | — |
| Thalangaha Estate | 56.4 | — | — |
| Thihagoda (ARG) | 50.0 | — | — |
| Trincomalee | 2.8 | 23.9 | 35.8 |
| Udugama (ARG) | 60.5 | — | — |
| Ukuwela | 0.5 | — | — |
| Upper Kotmale | 0.8 | — | — |
| Vavuniya | 0.0 | 26.0 | 35.5 |
| Victoria | 0.0 | — | — |

</details>

## Source data

[Download station observations](docs/dashboard/snapshot.json) · [Read the original weather report](docs/dashboard/report.pdf) · [Department of Meteorology](https://meteo.gov.lk/)

---

ClimateLog LK · Sri Lankan rainfall and temperature observations. Measurements use millimetres and degrees Celsius. [MIT license](LICENSE).
