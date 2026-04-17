# Metadata Tools

This directory contains starter scripts for enriching the Spectrascapes dataset with external data sources.

## KNMI Weather Data Fetcher

`knmi_weather_fetcher_starter.py` is a starter script that enriches `dataset/image_metadata.csv` with hourly meteorological observations from the [KNMI](https://www.knmi.nl/) (Royal Netherlands Meteorological Institute).

For each image, it finds the nearest KNMI weather station and retrieves:

| Parameter | Description |
|-----------|-------------|
| `T` (AirTemperature_C) | Air temperature at ~1.5m above ground (°C) |
| `N` (CloudCover_octas) | Cloud area fraction (0–8 octas) |

### Requirements

```bash
uv add requests
```

### Setup

1. **Obtain a free API key** from the KNMI Data Platform Developer Portal:  
   👉 https://developer.dataplatform.knmi.nl/
2. Open `knmi_weather_fetcher_starter.py` and set the `KNMI_API_KEY` variable at the top of the file to your key.

### Usage

```bash
uv run knmi_weather_fetcher_starter.py
```

This reads `dataset/image_metadata.csv` and outputs an enriched CSV to `scripts/metadata/image_metadata.csv` with four additional columns: `KNMI_Station`, `KNMI_StationDist_km`, `AirTemperature_C`, and `CloudCover_octas`.

### Notes

- The KNMI EDR API is **station-based** — it does not accept arbitrary lat/lon coordinates. The script automatically resolves the nearest weather station using Haversine distance.
- Duplicate queries (same station + same hour) are cached to minimise API calls.
- For production use or larger datasets, consider downloading the full KNMI dataset directly from their Open Data portal instead of querying the EDR API row-by-row:  
  👉 https://dataplatform.knmi.nl/dataset/hourly-in-situ-meteorological-observations-validated-1-0

---

## Very-High Resolution Satellite Imagery (Pleiades Neo) Tiles

`pleiades_tiles_creator.py` is a starter script that extracts square image tiles (currently set as 20m × 20m) from Pleiades Neo GeoTIFF satellite imagery, centred on the GPS coordinates from `dataset/image_metadata.csv`.

### Data Access

Pleiades Neo satellite imagery is distributed through the **ESA Third Party Missions programme**.

### Requirements

```bash
uv add rasterio pyproj
```

### Configuration

Edit the variables at the top of `pleiades_tile_extractor_starter.py`:

| Variable | Description | Default |
|----------|-------------|---------|
| `CITY` | City/area name to filter from metadata CSV | `"Arnhem"` |
| `PLEIADES_DIR` | Path to directory with Pleiades Neo `.TIF` files | `"../../dataset/PleiadesNeoData/IMG_01_PNEO3_PMS-FS"` |
| `OUTPUT_DIR` | Where to save tiles (`None` = inside `PLEIADES_DIR`) | `None` |
| `TILE_SIZE_M` | Side length of each tile in metres | `20` |
| `METRIC_CRS` | Projected CRS for metric buffering | `"EPSG:28992"` (Dutch RD New) |

### Usage

```bash
uv run pleiades_tile_extractor_starter.py
```

Tiles are saved as GeoTIFF files organized by variant (e.g. `RGB/`, `NED/`) inside the output directory.

### Notes

- If your study area is **outside the Netherlands**, change `METRIC_CRS` to a suitable local projected CRS (e.g. `"EPSG:32632"` for UTM zone 32N).
- Image locations that fall outside the Pleiades raster extent are silently skipped.
