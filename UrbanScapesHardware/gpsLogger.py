import gps
import csv
import os

LOG_FILE = 'gps_log.csv'
FIELDNAMES = ['timestamp', 'fix_status', 'latitude', 'longitude', 'altitude_m', 'speed_kmh', 'satellites_used']

try:
    session = gps.gps()  # Use default localhost and port
    session.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
    print("GPS session started successfully.")
except Exception as e:
    print(f"Error starting GPS session: {e}")

"""
    Fetches the latest TPV report from the GPS session.
    Converts speed to km/h and returns a dictionary of the data.
"""
def getCurrentLocationAndLogIt():
    if not session:
        print("GPS session not available.")
        return

    latest_tpv_report = None
    # Read all waiting reports and keep only the last TPV report
    while session.waiting(): # Check for data with a 1-second timeout
        report = session.next()
        if report['class'] == 'TPV':
            latest_tpv_report = report

    if latest_tpv_report:
        speed_mps = getattr(latest_tpv_report, 'speed', 0)
        speed_kmh = 'n/a'
        if isinstance(speed_mps, (int, float)):
            speed_kmh = speed_mps * 3.6

        location_data = {
            'timestamp': getattr(latest_tpv_report, 'time', 'n/a'),
            'fix_status': getattr(latest_tpv_report, 'mode', 1), # 1 = NO_FIX
            'latitude': getattr(latest_tpv_report, 'lat', 'n/a'),
            'longitude': getattr(latest_tpv_report, 'lon', 'n/a'),
            'altitude_m': getattr(latest_tpv_report, 'alt', 'n/a'),
            'speed_kmh': f"{speed_kmh:.2f}" if isinstance(speed_kmh, float) else speed_kmh,
            'satellites_used': len(getattr(latest_tpv_report, 'sats', [])) # 'sats' is a list of satellite objects
        }

        # --- Logging to CSV (no changes in logic here) ---
        file_exists = os.path.isfile(LOG_FILE)
        try:
            with open(LOG_FILE, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(location_data)
            print(f"Successfully logged latest location data: {location_data['timestamp']}")
        except Exception as e:
            print(f"Error logging location data to CSV: {e}")
    else:
        print("No fresh TPV report found in the buffer.")
