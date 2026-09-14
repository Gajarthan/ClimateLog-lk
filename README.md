<div align="center">

# ClimateLog LK

### Sri Lanka · Weather observation dashboard

**[Weather snapshot](#weather-snapshot) · [Sri Lanka map](#sri-lanka-map) · [Data quality](#data-quality) · [Station readings](#station-readings) · [Source data](#source-data)**

</div>

---

## Weather snapshot

**Report: 2026-09-14 · Period ending 08:30 SLST**

Captured 14 Sep 2026 · 15:32 SLST from the Department of Meteorology.

> This is a published snapshot, not a live feed. The date above identifies the data shown. Values are accurate to the report date shown.

![Weather overview for 2026-09-14: 60 station readings](docs/dashboard/overview.svg)

[Download observations](docs/dashboard/snapshot.json) · [View archived source PDF](docs/dashboard/report.pdf) · [Official source](https://meteo.gov.lk/)

## Sri Lanka map

![Sri Lanka station map with rainfall and daily maximum temperatures for 2026-09-14](docs/dashboard/sri-lanka-map.png)

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

**0 trace-rain readings** · **11 unresolved station identities** · **47 rows with unverified historical coordinates**

Missing readings are shown as **—**. Zero is a measured value; **Trace** is retained separately. Coverage describes this report, not the entire national station network. Station and coordinate flags remain available in the observation download. The map uses a separate published reference catalog; its historical positions do not verify current instrument locations.

## Station readings

<details>
<summary><strong>Open all 60 station readings</strong></summary>

| Station | Rain (mm) | Minimum (°C) | Maximum (°C) |
| --- | ---: | ---: | ---: |
| . Devidson TF (ARG) | 45.0 | — | — |
| Ambewela | 41.0 | — | — |
| Anuradhapura | 12.4 | 25.1 | 36.3 |
| Badulla | 5.9 | 20.7 | 30.5 |
| Balapitiya | 117.4 | — | — |
| Bandaragama | 147.3 | — | — |
| Bandaragama (ARG) | 147.0 | — | — |
| Bandarawela | 40.3 | 17.7 | 24.8 |
| Batticaloa | 0.0 | 26.0 | 34.1 |
| Benthotawatta | 114.6 | — | — |
| Bowatenna | 69.0 | — | — |
| Canyon | 11.0 | — | — |
| Castlereigh | 2.5 | — | — |
| Colombo | 0.7 | 27.3 | 31.2 |
| Devitura Estate (ARG) | 84.0 | — | — |
| Eladuwa Estate (ARG) | 63.0 | — | — |
| Elahara | 43.7 | — | — |
| Ellakanda Watta (ARG) | 76.5 | — | — |
| Galle | 131.7 | 23.6 | 29.4 |
| Hambantota | 1.0 | 26.4 | 33.1 |
| Handapanagala | 58.6 | — | — |
| Inginiyagala | 0.0 | — | — |
| Jaffna | 7.7 | 26.6 | 36.3 |
| Kandaketiya | 98.0 | — | — |
| Katugastota | 4.8 | 22.5 | 31.2 |
| Katunayake | 3.0 | 26.8 | 31.3 |
| Kesbewa (ARG) | 98.5 | — | — |
| Kotmale | 1.5 | — | — |
| Kukuleganaga | 48.0 | — | — |
| Kurunegala | 5.4 | 24.0 | 33.8 |
| Laxapana | 6.2 | — | — |
| Maha Illuppallama | 13.2 | 23.6 | 35.9 |
| Mannar | 0.1 | 25.8 | 31.8 |
| Maskeliya (DOM) | 0.0 | — | — |
| Mattala | 0.1 | 25.7 | 36.3 |
| Maussakele | 2.5 | — | — |
| Minneriya | 113.4 | — | — |
| Moneragala | 50.9 | 23.6 | 35.3 |
| Monrovia | 99.1 | — | — |
| Mullaitivu | 0.0 | 26.0 | 32.7 |
| Norton | 18.0 | — | — |
| Nuwara Eliya | 41.4 | 12.7 | 21.5 |
| Padukka Estate | 49.8 | — | — |
| Parangiyawadiya | 52.2 | — | — |
| Polonnaruwa | 1.7 | 24.1 | 38.6 |
| Pottuvil | 0.0 | 25.7 | 33.5 |
| Puttalam | 0.3 | 25.2 | 33.7 |
| Randenigala | 2.2 | — | — |
| Rantambe | 1.0 | — | — |
| Ratmalana | 10.4 | 26.6 | 32.4 |
| Ratnapura | 5.1 | 25.0 | 30.2 |
| Samanala Wawa | 0.0 | — | — |
| Sirikandura Estate (ARG) | 94.5 | — | — |
| Spring Valley | 56.0 | — | — |
| Trincomalee | 0.0 | 25.2 | 34.6 |
| Ukuwela | 8.9 | — | — |
| Upper Kotmale | 3.1 | — | — |
| Vavuniya | 21.7 | 24.4 | 37.6 |
| Victoria | 35.6 | — | — |
| Vithanakanda Estate (ARG) | 78.5 | — | — |

</details>

## Source data

[Download station observations](docs/dashboard/snapshot.json) · [Read the original weather report](docs/dashboard/report.pdf) · [Department of Meteorology](https://meteo.gov.lk/)

---

ClimateLog LK · Sri Lankan rainfall and temperature observations. Measurements use millimetres and degrees Celsius. [MIT license](LICENSE).
