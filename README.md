<div align="center">

# ClimateLog LK

### Sri Lanka · Weather observation dashboard

**[Weather snapshot](#weather-snapshot) · [Sri Lanka map](#sri-lanka-map) · [Data quality](#data-quality) · [Station readings](#station-readings) · [Source data](#source-data)**

</div>

---

## Weather snapshot

**Report: 2026-09-15 · Period ending 08:30 SLST**

Captured 15 Sep 2026 · 15:01 SLST from the Department of Meteorology.

> This is a published snapshot, not a live feed. The date above identifies the data shown. Values are accurate to the report date shown.

![Weather overview for 2026-09-15: 60 station readings](docs/dashboard/overview.svg)

[Download observations](docs/dashboard/snapshot.json) · [View archived source PDF](docs/dashboard/report.pdf) · [Official source](https://meteo.gov.lk/)

## Sri Lanka map

![Sri Lanka station map with rainfall and daily maximum temperatures for 2026-09-15](docs/dashboard/sri-lanka-map.png)

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

**0 trace-rain readings** · **14 unresolved station identities** · **44 rows with unverified historical coordinates**

Missing readings are shown as **—**. Zero is a measured value; **Trace** is retained separately. Coverage describes this report, not the entire national station network. Station and coordinate flags remain available in the observation download. The map uses a separate published reference catalog; its historical positions do not verify current instrument locations.

## Station readings

<details>
<summary><strong>Open all 60 station readings</strong></summary>

| Station | Rain (mm) | Minimum (°C) | Maximum (°C) |
| --- | ---: | ---: | ---: |
| Anuradhapura | 0.0 | 24.7 | 35.1 |
| Awissawella | 114.2 | — | — |
| Badulla | 0.0 | 20.8 | 30.2 |
| Bandarawela | 39.8 | 18.1 | 25.4 |
| Batticaloa | 0.8 | 26.4 | 32.6 |
| Batuwangala | 111.5 | — | — |
| Benthotawatta | 134.5 | — | — |
| Bowatenna | 5.4 | — | — |
| Canyon | 15.8 | — | — |
| Castlereigh | 9.0 | — | — |
| Colombo | 25.2 | 24.4 | 31.6 |
| Dunumale Estate (ARG) | 91.5 | — | — |
| Eladuwa Estate (ARG) | 118.5 | — | — |
| Ellakanda Watta (ARG) | 96.5 | — | — |
| Galle | 25.2 | 25.4 | 28.8 |
| Halwathura Estate (ARG) | 123.5 | — | — |
| Hambantota | 4.1 | 25.6 | 31.7 |
| Inginiyagala | 12.0 | — | — |
| Jaffna | 3.4 | 25.3 | 33.5 |
| Katugastota | 16.0 | 22.7 | 32.2 |
| Katunayake | 33.9 | 24.6 | 31.1 |
| Keenagahawila (ARG) | 114.5 | — | — |
| Keselhenawa (ARG) | 80.5 | — | — |
| Kethendola | 88.5 | — | — |
| Kirindiwela (ARG) | 147.0 | — | — |
| Kotmale | 0.0 | — | — |
| Kukuleganaga | 36.0 | — | — |
| Kuliyapitiya | 79.0 | — | — |
| Kurunegala | 0.4 | 24.3 | 35.2 |
| Laxapana | 6.4 | — | — |
| Madolthenna Estate (ARG) | 109.5 | — | — |
| Maha Illuppallama | 6.9 | 23.7 | 35.6 |
| Mannar | 0.0 | 25.3 | 34.1 |
| Maskeliya (DOM) | 21.5 | — | — |
| Mattala | 16.8 | 24.8 | 35.1 |
| Maussakele | 15.7 | — | — |
| Moneragala | 6.9 | 23.9 | 34.4 |
| Moraliya-Oya | 96.1 | — | — |
| Mullaitivu | 0.0 | 25.6 | 33.0 |
| Norton | 0.0 | — | — |
| Nuwara Eliya | 2.2 | 13.1 | 21.2 |
| Palanda(ARG) | 81.0 | — | — |
| Pasyala | 94.7 | — | — |
| Polonnaruwa | 0.0 | 25.0 | 35.5 |
| Pottuvil | 0.0 | 26.1 | 33.6 |
| Puttalam | 19.7 | 24.9 | 34.9 |
| Randenigala | 0.0 | — | — |
| Rantambe | 0.0 | — | — |
| Ratmalana | 62.1 | 23.4 | 32.6 |
| Ratnapura | 30.0 | 24.2 | 31.7 |
| Samanala Wawa | 55.0 | — | — |
| Thalduwa Estate (ARG) | 108.0 | — | — |
| Trincomalee | 0.0 | 24.4 | 33.4 |
| Udugama (ARG) | 80.0 | — | — |
| Ukuwela | 13.0 | — | — |
| Upper Kotmale | 9.4 | — | — |
| Vavuniya | 0.0 | 24.7 | 36.0 |
| Victoria | 1.2 | — | — |
| Warakapola | 87.9 | — | — |
| Wathupitiwala (ARG) | 86.0 | — | — |

</details>

## Source data

[Download station observations](docs/dashboard/snapshot.json) · [Read the original weather report](docs/dashboard/report.pdf) · [Department of Meteorology](https://meteo.gov.lk/)

---

ClimateLog LK · Sri Lankan rainfall and temperature observations. Measurements use millimetres and degrees Celsius. [MIT license](LICENSE).
