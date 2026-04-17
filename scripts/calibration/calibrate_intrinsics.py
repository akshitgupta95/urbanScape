import cv2
import numpy as np
import os
import json
import glob

# 8x11 squares = 7x10 internal intersections
CHECKERBOARD = (7, 10)
SQUARE_SIZE = 0.022  # 22mm converted to meters
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2) * SQUARE_SIZE

def calibrate_camera(image_paths, camera_name, is_thermal=False, is_rgn=False):
    objpoints = []
    imgpoints = []
    shape = None
    
    print(f"Finding corners for {camera_name} ({len(image_paths)} images)...")
    for path in image_paths:
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"Failed to load {path}")
            continue
        
        if is_thermal and img.dtype == np.uint16:
            gray = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        else:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
                
        if shape is None:
            shape = gray.shape[::-1]
            
        flags = None
        if not is_thermal:
            flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE + cv2.CALIB_CB_FAST_CHECK

        ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, flags=flags)
        if ret:
            corners2 = cv2.cornerSubPix(gray, corners, (2,2) if is_thermal else (11,11), (-1, -1), criteria)
            objpoints.append(objp)
            imgpoints.append(corners2)
            
    if not objpoints:
        print(f"Error: No corners found for {camera_name}!")
        return None
        
    print(f"Calibrating {camera_name} with {len(objpoints)} valid images...")
    
    calib_flags = cv2.CALIB_RATIONAL_MODEL
    if is_thermal:
        calib_flags += cv2.CALIB_ZERO_TANGENT_DIST
        
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, shape, None, None, flags=calib_flags)
    print(f"{camera_name} calibration RMS error: {ret}")
    
    return {
        "camera_matrix": mtx.tolist(),
        "distortion_coefficients": dist.tolist(),
        "resolution": list(shape)
    }

# --- Configuration ---
# Set this variable to the path where you downloaded the zenodo dataset.
# The path can be absolute or relative to this script.
DATASET_PATH = "../../dataset"
# ---------------------

def main():
    # Attempt to resolve the dataset directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if os.path.isabs(DATASET_PATH):
        dataset_dir = DATASET_PATH
    else:
        dataset_dir = os.path.abspath(os.path.join(script_dir, DATASET_PATH))
    
    base_dir = os.path.join(dataset_dir, "calibration", "calibration_plates", "instrinsic_target")
    
    rgb_imgs = glob.glob(os.path.join(base_dir, "RGB_intrinsic_target", "*.jpg"))
    rgn_imgs = glob.glob(os.path.join(base_dir, "RGN_intrinsic_target", "*.jpg"))
    thermal_imgs = glob.glob(os.path.join(base_dir, "Thermal_intrinsic_target", "*.jpg"))
    
    rgb_data = calibrate_camera(rgb_imgs, "RGB")
    rgn_data = calibrate_camera(rgn_imgs, "RGN", is_rgn=True)
    thermal_data = calibrate_camera(thermal_imgs, "Thermal", is_thermal=True)
    
    calibration_data = {}
    if rgb_data: calibration_data["rgb_camera"] = rgb_data
    if rgn_data: calibration_data["rgn_camera"] = rgn_data
    if thermal_data: calibration_data["thermal_camera"] = thermal_data
    
    out_path = os.path.join(dataset_dir, "calibration", "intrinsics.json")
    
    # Ensure intermediate directories exist just in case
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, "w") as f:
        json.dump(calibration_data, f, indent=4)
        
    print(f"\nSaved intrinsics to {out_path}")

if __name__ == "__main__":
    main()
