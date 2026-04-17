import csv
import os
import rasterio
from rasterio.windows import from_bounds
from pyproj import Transformer
import glob

"""
STARTER CODE: Pleiades Neo Tile Extractor

This script reads image_metadata.csv and, for each image location in the
specified CITY, extracts a square tile (default 20m × 20m) from Pleiades Neo 
GeoTIFF imagery centred on the image's GPS coordinates.

BEFORE RUNNING — Data Access:
  Pleiades Neo satellite imagery is distributed through the ESA Third Party 
  Missions programme. To obtain data for your study area:
    1. Register at: https://earth.esa.int/eogateway/
    2. Submit a project proposal via the ESA Third Party Programme:
       https://earth.esa.int/eogateway/search?category=Data&text=pleiades+neo
    3. Once approved, download the GeoTIFF product and point PLEIADES_DIR below
       to the folder containing the .TIF files.

The TIF files are expected to be in EPSG:4326 (WGS84). To compute an accurate
metric buffer, coordinates are temporarily projected to EPSG:28992 
(Amersfoort / RD New — the Dutch national grid), buffered, and projected back.
If your study area is outside the Netherlands, change METRIC_CRS below to a
suitable local projected CRS (e.g. a UTM zone).

Output tiles are saved as GeoTIFF files preserving the original CRS and
geotransform of the source raster.
"""

# --- Configuration ---
# City/area name to filter from image_metadata.csv (must match AreaName column).
CITY = "Arnhem"

# Path to the dataset metadata CSV.
DATASET_CSV = "../../dataset/image_metadata.csv"

# Path to the directory containing Pleiades Neo GeoTIFF (.TIF) files.
# Obtain this data from the ESA Third Party Missions programme:
#   https://earth.esa.int/eogateway/search?category=Data&text=pleiades+neo
PLEIADES_DIR = "../../dataset/PleiadesNeoData/IMG_01_PNEO3_PMS-FS"

# Output directory for extracted tiles.
# Set to None to save tiles in the same folder as the input Pleiades TIFs.
OUTPUT_DIR = None

# Tile side length in metres. # Change this if needed
TILE_SIZE_M = 20

# Metric CRS for computing accurate metre-based buffers.
# EPSG:28992 is the Dutch national grid (Amersfoort / RD New).
# Change this to a suitable local projected CRS for areas outside the Netherlands
# (e.g. "EPSG:32632" for UTM zone 32N covering central Europe).
METRIC_CRS = "EPSG:28992"
# ---------------------


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.abspath(os.path.join(script_dir, DATASET_CSV))
    pleiades_dir = os.path.abspath(os.path.join(script_dir, PLEIADES_DIR))

    # Default output to a "tiles" subfolder inside the Pleiades input directory
    if OUTPUT_DIR is None:
        output_dir = os.path.join(pleiades_dir, "tiles")
    else:
        output_dir = os.path.abspath(os.path.join(script_dir, OUTPUT_DIR))

    if not os.path.exists(csv_path):
        print(f"Error: Could not find metadata CSV at {csv_path}")
        return

    if not os.path.exists(pleiades_dir):
        print(f"Error: Could not find Pleiades directory at {pleiades_dir}")
        print("  Download Pleiades Neo data from the ESA Third Party Programme:")
        print("  https://earth.esa.int/eogateway/search?category=Data&text=pleiades+neo")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Discover all TIF files in the Pleiades directory
    tif_files = sorted(glob.glob(os.path.join(pleiades_dir, "*.TIF")))
    # Also check lowercase extension
    tif_files += sorted(glob.glob(os.path.join(pleiades_dir, "*.tif")))
    if not tif_files:
        print(f"Error: No TIF files found in {pleiades_dir}")
        return
    print(f"Found {len(tif_files)} TIF file(s) in Pleiades directory.")

    # Transformer: WGS84 (EPSG:4326) <-> metric CRS
    to_metric = Transformer.from_crs("EPSG:4326", METRIC_CRS, always_xy=True)
    to_wgs = Transformer.from_crs(METRIC_CRS, "EPSG:4326", always_xy=True)

    half = TILE_SIZE_M / 2.0  # half-side in metres

    # Read metadata and filter to the configured city (only _RGB to avoid triplicates)
    entries = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            area = row.get("AreaName", "")
            image_id = row.get("ImageID", "")
            if area == CITY and image_id.endswith("_RGB"):
                entries.append(row)

    if not entries:
        print(f"No entries found for city '{CITY}' in {csv_path}.")
        print(f"  Available areas: check the 'AreaName' column in your CSV.")
        return

    print(f"Found {len(entries)} {CITY} RGB entries in metadata.")
    print(f"Tile size: {TILE_SIZE_M}m × {TILE_SIZE_M}m")
    print(f"Output directory: {output_dir}\n")

    tiles_saved = 0
    for row in entries:
        image_id = row["ImageID"]
        lat = float(row["Latitude"])
        lon = float(row["Longitude"])

        # Project centre point to metric CRS, compute bounding box, project back
        cx, cy = to_metric.transform(lon, lat)
        min_x, min_y = cx - half, cy - half
        max_x, max_y = cx + half, cy + half

        # Back to WGS84 for the rasterio window
        min_lon, min_lat = to_wgs.transform(min_x, min_y)
        max_lon, max_lat = to_wgs.transform(max_x, max_y)

        print(f"[{image_id}] Centre: ({lat:.6f}, {lon:.6f})")

        # Try each TIF to find one that contains this bounding box
        for tif_path in tif_files:
            tif_name = os.path.basename(tif_path)
            with rasterio.open(tif_path) as src:
                # Check if the point falls within the raster bounds
                b = src.bounds
                if not (b.left <= lon <= b.right and b.bottom <= lat <= b.top):
                    continue

                # Clip the requested bbox to the raster bounds
                clip_left = max(min_lon, b.left)
                clip_bottom = max(min_lat, b.bottom)
                clip_right = min(max_lon, b.right)
                clip_top = min(max_lat, b.top)

                window = from_bounds(clip_left, clip_bottom, clip_right, clip_top, src.transform)

                # Read the windowed data
                data = src.read(window=window)

                if data.size == 0:
                    print(f"  ⚠️  Empty window from {tif_name}, skipping.")
                    continue

                # Build output path: one subfolder per TIF variant (NED, RGB, etc.)
                variant = tif_name.rsplit("_", 2)[-2] if "_" in tif_name else "unknown"
                variant_dir = os.path.join(output_dir, variant)
                os.makedirs(variant_dir, exist_ok=True)

                out_path = os.path.join(variant_dir, f"{image_id}_{variant}_{TILE_SIZE_M}m.tif")

                # Write the tile as a new GeoTIFF
                out_transform = rasterio.windows.transform(window, src.transform)
                profile = src.profile.copy()
                profile.update({
                    "width": data.shape[2],
                    "height": data.shape[1],
                    "transform": out_transform,
                })

                with rasterio.open(out_path, "w", **profile) as dst:
                    dst.write(data)

                print(f"  ✅ Saved {data.shape[2]}×{data.shape[1]} tile → {variant}/{os.path.basename(out_path)}")
                tiles_saved += 1

        print()

    print(f"Done! {tiles_saved} tile(s) saved to: {output_dir}")


if __name__ == "__main__":
    main()
