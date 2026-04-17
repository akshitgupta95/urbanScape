import csv
import os
import math
from datetime import datetime
try:
    import requests
except ImportError:
    print("Error: The 'requests' library is not installed. Please run: uv add requests")
    exit(1)

"""
STARTER CODE: KNMI Hourly Weather Data Fetcher

This is starter/example code to demonstrate how to enrich image metadata with
meteorological observations from KNMI (Royal Netherlands Meteorological Institute).
Adapt and extend it to suit your specific research needs.

What this script does:
  1. Reads dataset/image_metadata.csv (ImageID, Latitude, Longitude, CaptureTime).
  2. Finds the nearest KNMI weather station for each image via Haversine distance.
  3. Queries the KNMI EDR API for hourly validated observations at that station.
  4. Outputs an enriched CSV (scripts/metadata/image_metadata.csv) with:
       - N  : Cloud area fraction (octas, 0–8)
       - T  : Air temperature at ~1.5m (°C)

IMPORTANT — Before running:
  1. Obtain a free API key from the KNMI Data Platform Developer Portal:
     https://developer.dataplatform.knmi.nl/
  2. Set the KNMI_API_KEY variable below to your key.

For production use or larger datasets, consider downloading the full KNMI dataset
directly from their Open Data portal instead of querying the EDR API row-by-row:
  https://dataplatform.knmi.nl/dataset/hourly-in-situ-meteorological-observations-validated-1-0
The Open Data API provides bulk NetCDF/CSV file downloads which are more efficient
for large-scale analysis than the per-station EDR queries used here.

NOTE: The KNMI EDR API is station-based — you cannot query arbitrary lat/lon
coordinates. This script automatically resolves the nearest station for you.
"""

# --- Configuration ---
# 1. Obtain an API Key from the KNMI Data Platform Developer Portal:
#    https://developer.dataplatform.knmi.nl/
KNMI_API_KEY = "YOUR_API_KEY_HERE"

# 2. Paths
DATASET_CSV = "../../dataset/image_metadata.csv"

# 3. KNMI API Setup
COLLECTION_ID = "hourly-in-situ-meteorological-observations-validated"
BASE_URL = f"https://api.dataplatform.knmi.nl/edr/v1/collections/{COLLECTION_ID}"
# ---------------------


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two lat/lon points using the Haversine formula."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def fetch_all_stations(headers):
    """Fetch all KNMI station locations from the EDR /locations endpoint."""
    url = f"{BASE_URL}/locations"
    r = requests.get(url, headers=headers, params={"limit": 200, "f": "GeoJSON"})
    r.raise_for_status()
    features = r.json().get("features", [])
    stations = []
    for feat in features:
        coords = feat["geometry"]["coordinates"]  # [lon, lat]
        stations.append({
            "id": feat["id"],
            "name": feat["properties"].get("name", "Unknown"),
            "lon": coords[0],
            "lat": coords[1],
        })
    return stations


def find_nearest_station(lat, lon, stations):
    """Return the nearest station dict and its distance in km."""
    best, best_dist = None, float("inf")
    for s in stations:
        d = haversine_km(lat, lon, s["lat"], s["lon"])
        if d < best_dist:
            best, best_dist = s, d
    return best, best_dist


def query_station(station_id, dt_str, headers):
    """Query a specific station by its location ID for a given hourly datetime.
    Returns a dict of parameter_name -> value, or None on failure."""
    url = f"{BASE_URL}/locations/{station_id}"
    params = {"datetime": dt_str, "f": "CoverageJSON"}
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        return None, r.status_code, r.text

    data = r.json()
    result = {}
    # CoverageCollection wraps one or more Coverage objects
    if data.get("type") == "CoverageCollection":
        for cov in data.get("coverages", []):
            for key, rng in cov.get("ranges", {}).items():
                vals = rng.get("values", [])
                result[key] = vals[0] if vals else None
    elif data.get("type") == "Coverage":
        for key, rng in data.get("ranges", {}).items():
            vals = rng.get("values", [])
            result[key] = vals[0] if vals else None

    return result, 200, None


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.abspath(os.path.join(script_dir, DATASET_CSV))
    output_path = os.path.join(script_dir, "image_metadata.csv")

    if not KNMI_API_KEY or KNMI_API_KEY == "YOUR_API_KEY_HERE":
        print("=========================================================")
        print("⚠️  MISSING KNMI API KEY")
        print("Please edit this script and set the KNMI_API_KEY variable")
        print("You can get one at: https://developer.dataplatform.knmi.nl/")
        print("=========================================================")
        return

    if not os.path.exists(csv_path):
        print(f"Error: Could not find metadata CSV at {csv_path}")
        return

    headers = {
        "Authorization": KNMI_API_KEY,
        "Accept": "application/json"
    }

    # --- Step 1: fetch all station locations once ---
    print("Fetching KNMI station catalogue...")
    stations = fetch_all_stations(headers)
    print(f"  Found {len(stations)} weather stations.\n")

    # --- Step 2: read all rows, enrich with weather data ---
    # Cache: (station_id, dt_str) -> result dict, to avoid duplicate API calls
    query_cache = {}
    enriched_rows = []

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        input_fieldnames = reader.fieldnames
        
        for row in reader:
            image_id = row.get("ImageID", "")
            lat = row.get("Latitude")
            lon = row.get("Longitude")
            cap_time = row.get("CaptureTime")

            # Default new columns
            row["KNMI_Station"] = ""
            row["KNMI_StationDist_km"] = ""
            row["AirTemperature_C"] = ""
            row["CloudCover_octas"] = ""

            if not lat or not lon or not cap_time:
                print(f"[{image_id}] Skipping — missing coordinates or time.")
                enriched_rows.append(row)
                continue

            lat_f, lon_f = float(lat), float(lon)

            # Find nearest station
            station, dist_km = find_nearest_station(lat_f, lon_f, stations)
            if station is None:
                print(f"[{image_id}] No stations found!")
                enriched_rows.append(row)
                continue

            # Round CaptureTime down to the nearest hour (dataset is hourly)
            dt_obj = datetime.fromisoformat(cap_time)
            dt_hour = dt_obj.replace(minute=0, second=0, microsecond=0)
            dt_str = dt_hour.strftime("%Y-%m-%dT%H:%M:%SZ")

            cache_key = (station["id"], dt_str)

            if cache_key in query_cache:
                result = query_cache[cache_key]
                print(f"[{image_id}] Using cached result for {station['name']} @ {dt_str}")
            else:
                print(f"[{image_id}] Querying {station['name']} ({dist_km:.1f} km) @ {dt_str}...")
                result, status, err = query_station(station["id"], dt_str, headers)
                if status != 200:
                    print(f"  ❌ API error {status}: {err}")
                    result = {}
                query_cache[cache_key] = result

            air_temp = result.get("T", "")
            cloud_cover = result.get("N", "")

            row["KNMI_Station"] = station["name"]
            row["KNMI_StationDist_km"] = f"{dist_km:.1f}"
            row["AirTemperature_C"] = air_temp if air_temp != "" else ""
            row["CloudCover_octas"] = cloud_cover if cloud_cover != "" else ""

            if air_temp != "" or cloud_cover != "":
                print(f"  ✅ T={air_temp} °C, N={cloud_cover} octas")

            enriched_rows.append(row)

    # --- Step 3: write enriched CSV ---
    output_fieldnames = list(input_fieldnames) + ["KNMI_Station", "KNMI_StationDist_km", "AirTemperature_C", "CloudCover_octas"]

    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(enriched_rows)

    print(f"\n✅ Enriched metadata saved to: {output_path}")
    print(f"   {len(enriched_rows)} rows written, {len(query_cache)} unique API queries made.")


if __name__ == "__main__":
    main()
