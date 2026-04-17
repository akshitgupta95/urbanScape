import cv2
import numpy as np
import os
import json
import matplotlib.pyplot as plt

CHECKERBOARD = (7, 10)
SQUARE_SIZE = 0.022
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2) * SQUARE_SIZE

def load_intrinsics(path):
    with open(path, 'r') as f:
        data = json.load(f)
    return data

def process_pairs(pair_dir, name1, name2, is_thermal=False):
    print(f"Processing extrinsic pairs from {pair_dir} for {name1}-{name2}...")
    subdirs = sorted([os.path.join(root, d) for root, dirs, _ in os.walk(pair_dir) for d in dirs])
    
    objpoints = []
    imgpoints1 = []
    imgpoints2 = []
    pair_names = []
    
    for subdir in subdirs:
        rgb_path = os.path.join(subdir, 'RGB.jpg')
        if not os.path.exists(rgb_path):
            rgb_path = os.path.join(subdir, 'rgb.jpg')
            
        other_path = os.path.join(subdir, 'thermal_image.jpg' if is_thermal else 'rgn.jpg')
        
        if os.path.exists(rgb_path) and os.path.exists(other_path):
            img1 = cv2.imread(rgb_path)
            img2 = cv2.imread(other_path, cv2.IMREAD_UNCHANGED)
            
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            if is_thermal:
                if img2.dtype == np.uint16:
                    gray2 = cv2.normalize(img2, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                else:
                    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2
            else:
                gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2

            shape1 = gray1.shape[::-1]
            shape2 = gray2.shape[::-1]
            
            flags1 = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE + cv2.CALIB_CB_FAST_CHECK
            flags2 = None if is_thermal else flags1
            
            ret1, corners1 = cv2.findChessboardCorners(gray1, CHECKERBOARD, flags=flags1)
            ret2, corners2 = cv2.findChessboardCorners(gray2, CHECKERBOARD, flags=flags2)
            
            if ret1 and ret2:
                corners2_1 = cv2.cornerSubPix(gray1, corners1, (11,11), (-1, -1), criteria)
                corners2_2 = cv2.cornerSubPix(gray2, corners2, (2,2) if is_thermal else (21,21), (-1, -1), criteria)
                
                # SMART FIX: Check Origin Alignment to fix orientation issues
                dim_rgb = np.array(shape1)
                dim_other = np.array(shape2)
                
                pt_rgb_first = corners2_1[0][0]
                pt_other_first = corners2_2[0][0]
                pt_other_last = corners2_2[-1][0]
                
                norm_rgb_first = pt_rgb_first / dim_rgb
                norm_other_first = pt_other_first / dim_other
                norm_other_last = pt_other_last / dim_other
                
                if np.linalg.norm(norm_rgb_first - norm_other_last) < np.linalg.norm(norm_rgb_first - norm_other_first):
                    corners2_2 = corners2_2[::-1].copy()
                    
                objpoints.append(objp)
                imgpoints1.append(corners2_1)
                imgpoints2.append(corners2_2)
                pair_names.append(os.path.basename(subdir))
                
    print(f"Found {len(objpoints)} valid stereo pairs out of {len(subdirs)} subdirectories.")
    return objpoints, imgpoints1, imgpoints2, shape1, shape2, pair_names

def calibrate_stereo(intrinsics, objpoints, imgpoints_rgb, imgpoints_other, shape_other, is_thermal=False):
    mtx_rgb = np.array(intrinsics['rgb_camera']['camera_matrix'])
    dist_rgb = np.array(intrinsics['rgb_camera']['distortion_coefficients'])
    
    other_key = 'thermal_camera' if is_thermal else 'rgn_camera'
    mtx_other = np.array(intrinsics[other_key]['camera_matrix'])
    dist_other = np.array(intrinsics[other_key]['distortion_coefficients'])

    # Apply scaling for RGB matrix and points when calibrating against Thermal (resolution difference)
    imgpoints_rgb_to_use = imgpoints_rgb
    mtx_rgb_to_use = mtx_rgb.copy()
    
    if is_thermal:
        shape_rgb = intrinsics['rgb_camera']['resolution']
        scale_x = shape_other[0] / shape_rgb[0]
        scale_y = shape_other[1] / shape_rgb[1]
        
        mtx_rgb_to_use[0, 0] *= scale_x
        mtx_rgb_to_use[0, 2] *= scale_x
        mtx_rgb_to_use[1, 1] *= scale_y
        mtx_rgb_to_use[1, 2] *= scale_y
        
        imgpoints_rgb_to_use = []
        for pts in imgpoints_rgb:
            pts_scaled = pts.copy()
            pts_scaled[:, :, 0] *= scale_x
            pts_scaled[:, :, 1] *= scale_y
            imgpoints_rgb_to_use.append(pts_scaled)
            
    flags_stereo = cv2.CALIB_FIX_INTRINSIC + cv2.CALIB_RATIONAL_MODEL
    criteria_stereo = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-6)

    print("Running stereoCalibrate...")
    ret, _, _, _, _, R, T, E, F = cv2.stereoCalibrate(
        objpoints, imgpoints_rgb_to_use, imgpoints_other,
        mtx_rgb_to_use, dist_rgb,
        mtx_other, dist_other,
        shape_other, criteria=criteria_stereo, flags=flags_stereo
    )
    
    print(f"Stereo calibration RMS error: {ret}")
    
    return {
        "rotation_matrix_R": R.tolist(),
        "translation_vector_T": T.tolist(),
        "essential_matrix_E": E.tolist(),
        "fundamental_matrix_F": F.tolist()
    }, ret
# --- Configuration ---
# Set this variable to the path where you downloaded the zenodo dataset.
# The path can be absolute or relative to this script.
DATASET_PATH = "../../dataset"
# ---------------------

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if os.path.isabs(DATASET_PATH):
        dataset_dir = DATASET_PATH
    else:
        dataset_dir = os.path.abspath(os.path.join(script_dir, DATASET_PATH))
        
    intrinsics_path = os.path.join(dataset_dir, "calibration", "intrinsics.json")
    extrinsics_path = os.path.join(dataset_dir, "calibration", "extrinsics.json")
    
    if not os.path.exists(intrinsics_path):
        print(f"Error: Intrinsics file {intrinsics_path} not found. Please run calibrate_intrinsics.py first.")
        return
        
    intrinsics = load_intrinsics(intrinsics_path)
    
    base_dir = os.path.join(dataset_dir, "calibration", "calibration_plates", "extrinsic_target_pairs")
    
    output = {}
    
    # Process RGB-RGN
    rgn_dir = os.path.join(base_dir, "RGB_RGN")
    if os.path.exists(rgn_dir):
        obj_rgn, img_rgb_rgn, img_rgn, _, shape_rgn, _ = process_pairs(rgn_dir, "RGB", "RGN", is_thermal=False)
        if obj_rgn:
            rgn_extrinsics, rgn_rms = calibrate_stereo(intrinsics, obj_rgn, img_rgb_rgn, img_rgn, shape_rgn, is_thermal=False)
            output["stereo_extrinsics_rgn_rgb"] = rgn_extrinsics
            output["calibration_error_rms_rgn_rgb"] = rgn_rms
    else:
        print(f"Warning: Extrinsic pair directory not found: {rgn_dir}")
        
    # Process RGB-Thermal
    thr_dir = os.path.join(base_dir, "RGB_Thermal")
    if os.path.exists(thr_dir):
        obj_thr, img_rgb_thr, img_thr, _, shape_thr, _ = process_pairs(thr_dir, "RGB", "Thermal", is_thermal=True)
        if obj_thr:
            thr_extrinsics, thr_rms = calibrate_stereo(intrinsics, obj_thr, img_rgb_thr, img_thr, shape_thr, is_thermal=True)
            output["stereo_extrinsics_thermal_rgb"] = thr_extrinsics
            output["calibration_error_rms_thermal_rgb"] = thr_rms
    else:
        print(f"Warning: Extrinsic pair directory not found: {thr_dir}")
        
    if output:
        with open(extrinsics_path, "w") as f:
            json.dump(output, f, indent=4)
        print(f"\nSaved extrinsics to {extrinsics_path}")
    else:
        print("\nNo pairs were processed. Extrinsics not saved.")

if __name__ == "__main__":
    main()
