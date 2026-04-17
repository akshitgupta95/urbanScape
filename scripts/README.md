# Scripts

This directory contains Python-based tooling for working with the **Spectrascapes** dataset. The scripts are organised into three sub-directories, each serving a distinct purpose:

| Directory | Purpose |
|-----------|---------|
| [`calibration/`](calibration/) | Camera intrinsic & extrinsic calibration and stereo rectification |
| [`metadata/`](metadata/) | Enriching dataset metadata with weather data and satellite imagery tiles |
| [`usecases/`](usecases/) | Example analysis workflows that demonstrate how to work with the dataset |

---

## Prerequisites

### Python

The project requires **Python ≥ 3.12**. The exact version is pinned in `.python-version`.

### uv – Python project & package manager

All scripts in this directory are managed as a single **[uv](https://docs.astral.sh/uv/)** project (`pyproject.toml` + `uv.lock`).  
If you do not have `uv` installed, follow the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/).

Quick install (macOS / Linux):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Environment Setup

From the `scripts/` directory, run:

```bash
# Create the virtual environment and install all locked dependencies in one step
uv sync
```

This reads `pyproject.toml` and `uv.lock`, creates a `.venv/` in the current directory, and installs every dependency at the exact locked version — ensuring reproducible results across machines.

### Current dependencies (from `pyproject.toml`)

| Package | Minimum Version | Used By |
|---------|----------------|---------|
| `matplotlib` | ≥ 3.10.8 | `calibration/`, `usecases/` |
| `opencv-python` | ≥ 4.13.0.92 | `calibration/`, `usecases/` |
| `pyproj` | ≥ 3.7.2 | `metadata/` (Pleiades tile extraction) |
| `rasterio` | ≥ 1.5.0 | `metadata/` (Pleiades tile extraction) |
| `ultralytics` | ≥ 8.4.38 | `usecases/` (SAM segmentation model) |

> **Note:** Individual sub-directory READMEs may list `uv add <pkg>` commands for clarity, but if you have already run `uv sync` at the project root then all dependencies are already installed. The `uv add` commands are only needed if you are adding a new package to the project.

### Optional dependencies

Some scripts use packages from the Python standard library or optional external services:

- **`requests`** — used by `knmi_weather_fetcher_starter.py` to query the KNMI API. Install with `uv add requests` if not already present.
- **`scipy`** — used by the use-case analysis script for ANOVA and Tukey's HSD tests. Install with `uv add scipy` if you want statistical analysis output.

---

## Running Scripts

All scripts should be executed via `uv run` from the `scripts/` directory so that the correct virtual environment and dependencies are used automatically:

```bash
# General pattern
uv run <subdirectory>/<script_name>.py
```

---

## Calibration Tools — `calibration/`

This directory contains the tools needed to perform **intrinsic** and **extrinsic (stereo)** camera calibrations for the RGB, RGN, and Thermal camera setups. The generated calibration models are saved as `intrinsics.json` and `extrinsics.json` inside the dataset.

For the full documentation, see [`calibration/README.md`](calibration/README.md).

### Quick Reference

Before running the calibration scripts, you can optionally edit the `DATASET_PATH` variable at the top of each script to point to the base directory where the Zenodo `dataset` was downloaded.

#### 1. Calibrate Intrinsics

Calibrates all individual cameras and exports their parameters independently:

```bash
uv run calibration/calibrate_intrinsics.py
```

**Output:** `dataset/calibration/intrinsics.json`

#### 2. Calibrate Extrinsics

Computes cross-camera coordinate mappings using RGB as the reference camera:

```bash
uv run calibration/calibrate_extrinsics.py
```

**Output:** `dataset/calibration/extrinsics.json`

#### 3. Stereo Rectification (Starter)

Loops through the image dataset and produces stereo-rectified images using the calibration matrices:

```bash
uv run calibration/rectify_dataset_starter.py
```

> **Note:** This starter script uses pairwise rectification with RGB as origin. RGN and Thermal are aligned independently to RGB, so they will not be perfectly epipolar-aligned to each other. Use this as a foundation for more advanced registration routines.

### Data Notes

- Expected directory structures: `dataset/calibration/calibration_plates/instrinsic_target` and `dataset/calibration/calibration_plates/extrinsic_target_pairs`.
- The `SQUARE_SIZE` parameter is fixed at **0.022 m (22 mm)**.
- High-contrast inversion for Thermal and RGN images is handled automatically inside `calibrate_extrinsics.py`.

---

## Metadata Tools — `metadata/`

This directory contains starter scripts for enriching the Spectrascapes dataset with external data sources: meteorological observations and very-high-resolution satellite imagery.

For the full documentation, see [`metadata/README.md`](metadata/README.md).

### KNMI Weather Data Fetcher

`knmi_weather_fetcher_starter.py` enriches `dataset/image_metadata.csv` with hourly meteorological observations from the [KNMI](https://www.knmi.nl/) (Royal Netherlands Meteorological Institute).

For each image, it finds the nearest KNMI weather station and retrieves:

| Parameter | Description |
|-----------|-------------|
| `T` (AirTemperature_C) | Air temperature at ~1.5 m above ground (°C) |
| `N` (CloudCover_octas) | Cloud area fraction (0–8 octas) |

#### Setup

1. Obtain a free API key from the [KNMI Data Platform Developer Portal](https://developer.dataplatform.knmi.nl/).
2. Set the `KNMI_API_KEY` variable at the top of the script.

#### Usage

```bash
uv run metadata/knmi_weather_fetcher_starter.py
```

**Output:** `scripts/metadata/image_metadata.csv` — the original CSV with four additional columns: `KNMI_Station`, `KNMI_StationDist_km`, `AirTemperature_C`, and `CloudCover_octas`.

### Pleiades Neo Satellite Tile Extractor

`pleiades_tiles_creator.py` extracts square tiles (default 20 m × 20 m) from Pleiades Neo GeoTIFF satellite imagery, centred on GPS coordinates from `dataset/image_metadata.csv`.

| Variable | Description | Default |
|----------|-------------|---------|
| `CITY` | City/area name to filter from metadata | `"Arnhem"` |
| `PLEIADES_DIR` | Path to directory with Pleiades Neo `.TIF` files | `"../../dataset/PleiadesNeoData/IMG_01_PNEO3_PMS-FS"` |
| `OUTPUT_DIR` | Where to save tiles (`None` = inside `PLEIADES_DIR`) | `None` |
| `TILE_SIZE_M` | Side length of each tile in metres | `20` |
| `METRIC_CRS` | Projected CRS for metric buffering | `"EPSG:28992"` (Dutch RD New) |

#### Usage

```bash
uv run metadata/pleiades_tiles_creator.py
```

> **Tip:** If your study area is outside the Netherlands, change `METRIC_CRS` to a suitable local projected CRS (e.g. `"EPSG:32632"` for UTM zone 32N).

---

## Use Cases — `usecases/`

This directory contains example analysis scripts that demonstrate practical workflows with the Spectrascapes dataset.

### Near-Infrared Channel Analysis

`use_case_analysis_nearInfrared_channel.py` provides an interactive pipeline for analysing near-infrared (NIR) reflectance differences across building façade materials. The workflow:

1. **ROI Selection** — Interactively select 10 regions of interest (ROIs) for each of three groups: *Left Façade*, *Right Façade*, and *Glass*.
2. **Semantic Segmentation (optional)** — If the [Ultralytics SAM](https://docs.ultralytics.com/models/sam/) model is available, the selected bounding boxes are refined using the Segment Anything Model for more precise material boundaries. If not installed, rectangular ROIs are used instead.
3. **Statistical Analysis** — Performs a One-Way ANOVA and Tukey's HSD test (requires `scipy`) to determine whether NIR reflectance values differ significantly between the three surface groups.
4. **Visualisation** — Generates a box plot with jitter overlay (`roi_boxplot.png`) and a SAM-masks overlay image (`sam_masks_overlay.jpg`).

#### Usage

```bash
uv run usecases/use_case_analysis_nearInfrared_channel.py
```

The script operates on `usecasecropped.png` (included in the directory). Edit the `INPUT_IMAGE` variable at the top of the file to use a different image.

---

## Repository Structure

```
scripts/
├── .python-version          # Pinned Python version (3.12)
├── pyproject.toml           # uv project definition & dependencies
├── uv.lock                  # Locked dependency versions (reproducible installs)
├── main.py                  # Project entry point placeholder
├── README.md                # ← You are here
│
├── calibration/
│   ├── README.md            # Full calibration documentation
│   ├── calibrate_intrinsics.py
│   ├── calibrate_extrinsics.py
│   └── rectify_dataset_starter.py
│
├── metadata/
│   ├── README.md            # Full metadata tools documentation
│   ├── knmi_weather_fetcher_starter.py
│   └── pleiades_tiles_creator.py
│
└── usecases/
    ├── use_case_analysis_nearInfrared_channel.py
    └── usecasecropped.png   # Sample input image
```

---

## Reproducing Results

To fully reproduce the results from the Spectrascapes dataset:

1. **Download the dataset** from the Zenodo repository and place it alongside this repository (or adjust `DATASET_PATH` in the relevant scripts).

2. **Install the environment:**

   ```bash
   cd scripts
   uv sync
   ```

3. **Run calibration** (if regenerating calibration matrices):

   ```bash
   uv run calibration/calibrate_intrinsics.py
   uv run calibration/calibrate_extrinsics.py
   ```

4. **Run metadata enrichment** (optional — requires API keys / satellite data):

   ```bash
   uv run metadata/knmi_weather_fetcher_starter.py
   uv run metadata/pleiades_tiles_creator.py
   ```

5. **Run use-case analysis:**

   ```bash
   uv run usecases/use_case_analysis_nearInfrared_channel.py
   ```

> **Tip:** Each sub-directory contains its own `README.md` with more detailed instructions, configuration options, and notes. Refer to those for script-specific guidance.
