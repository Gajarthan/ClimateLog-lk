# Map sources and location notes

The map plots only explicit station-name matches. It does not estimate rainfall
between stations, geocode unknown names, or change the stored observation values.

- **Outline:** Natural Earth 1:50m Admin 0 Countries, Sri Lanka geometry. [Dataset](https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries-2/). [Public-domain terms](https://www.naturalearthdata.com/about/terms-of-use/).
- **Reference positions:** NOAA NCEI Integrated Surface Database [station history](https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv), retrieved 13 September 2026. Matching ignores spaces; Mullaittivu is matched to Mullaitivu as a spelling variant. Source identifiers, coordinates, record dates, and source-file checksum are stored in [the map catalog](../../src/weather_lk/stations/data/map_stations.json).
- **Measurements:** The dated Department of Meteorology report linked in the dashboard. These values are not NOAA weather measurements.

Sixteen stations in the current snapshot have catalog matches. Remaining stations
stay in the readings table. The NOAA positions are historical references, not
independently verified current instrument positions. Boundary simplification and
coastal stations can place a marker just outside the drawn coastline. Legacy
coordinate quality flags remain unchanged in the observation download.

The map is regenerated from each successfully published snapshot by the GitHub
Actions dashboard refresh. It uses packaged reference data and needs no map API
key or additional geospatial dependency at runtime.
