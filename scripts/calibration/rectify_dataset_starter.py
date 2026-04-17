import cv2
import numpy as np
import os
import glob
import json

"""
STARTER CODE: 3-imaging sensors Stereo Rectification

IMPLICATIONS & LIMITATIONS:
This script performs pairwise stereo rectification for a 3-imaging sensor system (RGB, RGN, Thermal) 
by using the RGB camera as the common origin. 

In two-camera stereo rectification, both cameras are mathematically rotated so their epipolar 
lines are perfectly horizontal. However, because RGB is paired with both RGN and Thermal independently:
1. The rotation (R1) applied to RGB to align with RGN is DIFFERENT from the rotation applied to align with Thermal.
2. In this starter script, we save the rectified RGB image based on the RGB-RGN transformation.
3. We save the Thermal image based on the RGB-Thermal transformation.

As a result, while RGN and RGB will share perfectly horizontal epipolar lines, the Thermal image 
will be slightly offset relative to this specific RGB projection. True unified multi-camera rectification 
would require projecting all auxiliary cameras onto a single, fixed virtual plane, or using disparity-based 
inverse warping. This script provides a solid base for pairwise evaluation and basic registration.
"""

# --- Configuration ---
# Set this variable to the path where you downloaded the zenodo dataset.
DATASET_PATH = "../../dataset"
INPUT_DIR = "image_data/<city>"
OUTPUT_DIR = "processed_image_data/<city>"

# alpha=0 crops out black borders (valid pixels only).
# alpha=1.0 keeps all original pixels (no zoom-in).
# alpha=-1 yields default optimal scaling.
ALPHA = -1
# ---------------------

def get_scaled_matrix(mtx, scale_x, scale_y):
    m = mtx.copy()
    m[0, 0] *= scale_x
    m[0, 2] *= scale_x
    m[1, 1] *= scale_y
    m[1, 2] *= scale_y
    return m

def get_scaled_P(P, scale_x, scale_y):
    Ps = P.copy()
    Ps[0, 0] *= (1.0 / scale_x)
    Ps[0, 2] *= (1.0 / scale_x)
    Ps[1, 1] *= (1.0 / scale_y)
    Ps[1, 2] *= (1.0 / scale_y)
    if Ps.shape[1] > 3:
        Ps[0, 3] *= (1.0 / scale_x)
    return Ps


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if os.path.isabs(DATASET_PATH):
        dataset_dir = DATASET_PATH
    else:
        dataset_dir = os.path.abspath(os.path.join(script_dir, DATASET_PATH))
        
    intrinsics_path = os.path.join(dataset_dir, "calibration", "intrinsics.json")
    extrinsics_path = os.path.join(dataset_dir, "calibration", "extrinsics.json")
    
    if not os.path.exists(intrinsics_path) or not os.path.exists(extrinsics_path):
        print("Error: Calibration JSON files missing. Run calibration scripts first.")
        return
        
    with open(intrinsics_path, "r") as f:
        intrinsics = json.load(f)
    with open(extrinsics_path, "r") as f:
        extrinsics = json.load(f)
        
    print("Loading calibration parameters...")
    
    # Extrinsics
    R_rgn = np.array(extrinsics["stereo_extrinsics_rgn_rgb"]["rotation_matrix_R"])
    T_rgn = np.array(extrinsics["stereo_extrinsics_rgn_rgb"]["translation_vector_T"])
    
    R_therm = np.array(extrinsics["stereo_extrinsics_thermal_rgb"]["rotation_matrix_R"])
    T_therm = np.array(extrinsics["stereo_extrinsics_thermal_rgb"]["translation_vector_T"])
    
    # Intrinsics
    mtx_rgb = np.array(intrinsics["rgb_camera"]["camera_matrix"])
    dist_rgb = np.array(intrinsics["rgb_camera"]["distortion_coefficients"])
    w_rgb, h_rgb = intrinsics["rgb_camera"]["resolution"]
    
    mtx_rgn = np.array(intrinsics["rgn_camera"]["camera_matrix"])
    dist_rgn = np.array(intrinsics["rgn_camera"]["distortion_coefficients"])
    w_rgn, h_rgn = intrinsics["rgn_camera"]["resolution"]
    
    mtx_therm = np.array(intrinsics["thermal_camera"]["camera_matrix"])
    dist_therm = np.array(intrinsics["thermal_camera"]["distortion_coefficients"])
    w_therm, h_therm = intrinsics["thermal_camera"]["resolution"]
    
    # Historically in rectification.py, thermal lens distortion was locked to zero during stereoRectify 
    dist_thermal_fixed = np.zeros(5, dtype=np.float32)

    print("Pre-calculating Stereo Rectification Maps...")
    # --- RGB-RGN Maps ---
    scale_x_rgn = w_rgn / w_rgb
    scale_y_rgn = h_rgn / h_rgb
    mtx_rgb_rgn_scaled = get_scaled_matrix(mtx_rgb, scale_x_rgn, scale_y_rgn)
    
    R1_rgn, R2_rgn, P1_rgn, P2_rgn, Q_rgn, roi1_rgn, roi2_rgn = cv2.stereoRectify(
        mtx_rgb_rgn_scaled, dist_rgb, mtx_rgn, dist_rgn, (w_rgn, h_rgn), R_rgn, T_rgn, alpha=ALPHA, newImageSize=(w_rgn, h_rgn)
    )
    
    P1_rgn_scaled = get_scaled_P(P1_rgn, scale_x_rgn, scale_y_rgn)
    P2_rgn_scaled = get_scaled_P(P2_rgn, scale_x_rgn, scale_y_rgn)
    
    map1_rgb_primary, map2_rgb_primary = cv2.initUndistortRectifyMap(mtx_rgb, dist_rgb, R1_rgn, P1_rgn_scaled, (w_rgb, h_rgb), cv2.CV_16SC2)
    map1_rgn, map2_rgn = cv2.initUndistortRectifyMap(mtx_rgn, dist_rgn, R2_rgn, P2_rgn_scaled, (w_rgb, h_rgb), cv2.CV_16SC2)

    # --- RGB-Thermal Maps ---
    scale_x_therm = w_therm / w_rgb
    scale_y_therm = h_therm / h_rgb
    mtx_rgb_therm_scaled = get_scaled_matrix(mtx_rgb, scale_x_therm, scale_y_therm)
    
    R1_therm, R2_therm, P1_therm, P2_therm, Q_therm, roi1_therm, roi2_therm = cv2.stereoRectify(
        mtx_rgb_therm_scaled, dist_rgb, mtx_therm, dist_thermal_fixed, (w_therm, h_therm), R_therm, T_therm, alpha=ALPHA, newImageSize=(w_therm, h_therm)
    )
    
    # We do not need the scaled RGB-Thermal P1 map because we'll use the RGB image from the RGN pair 
    # to serve as the unified origin, since RGN resolution/alignment is more critical.
    # We just need the Thermal remapping coordinate scaling:
    P2_therm_scaled = get_scaled_P(P2_therm, scale_x_therm, scale_y_therm)
    map1_therm, map2_therm = cv2.initUndistortRectifyMap(mtx_therm, dist_thermal_fixed, R2_therm, P2_therm_scaled, (w_rgb, h_rgb), cv2.CV_16SC2)
    
    # --- Process the Dataset ---
    input_base = os.path.join(dataset_dir, INPUT_DIR)
    output_base = os.path.join(dataset_dir, OUTPUT_DIR)
    
    rgb_in_dir = os.path.join(input_base, "RGB")
    rgn_in_dir = os.path.join(input_base, "RGN")
    therm_in_dir = os.path.join(input_base, "Thermal")
    
    if not os.path.exists(rgb_in_dir):
        print(f"Error: Input directory {rgb_in_dir} not found.")
        return
        
    rgb_out_dir = os.path.join(output_base, "RGB")
    rgn_out_dir = os.path.join(output_base, "RGN")
    therm_out_dir = os.path.join(output_base, "Thermal")
    
    os.makedirs(rgb_out_dir, exist_ok=True)
    os.makedirs(rgn_out_dir, exist_ok=True)
    os.makedirs(therm_out_dir, exist_ok=True)
    
    rgb_files = glob.glob(os.path.join(rgb_in_dir, "*_RGB.*"))
    print(f"\nFound {len(rgb_files)} RGB pairs. Starting processing...")
    
    for rgb_path in rgb_files:
        basename = os.path.basename(rgb_path)
        prefix = basename.rsplit("_RGB", 1)[0]
        ext = basename.rsplit("_RGB", 1)[1]
        
        rgn_path = os.path.join(rgn_in_dir, f"{prefix}_RGN{ext}")
        therm_path = os.path.join(therm_in_dir, f"{prefix}_Thermal{ext}")
        
        print(f" -> Mapping pair: {prefix}")
        
        img_rgb = cv2.imread(rgb_path)
        if img_rgb is None:
            continue
            
        # 1. Remap RGB using the primary (RGN) R1 transform. This sets the canonical unified perspective.
        rectified_rgb = cv2.remap(img_rgb, map1_rgb_primary, map2_rgb_primary, cv2.INTER_LINEAR)
        cv2.imwrite(os.path.join(rgb_out_dir, f"{prefix}_RGB{ext}"), rectified_rgb)
        
        # 2. Process RGN if it exists
        if os.path.exists(rgn_path):
            img_rgn = cv2.imread(rgn_path)
            if img_rgn is not None:
                rectified_rgn = cv2.remap(img_rgn, map1_rgn, map2_rgn, cv2.INTER_LINEAR)
                cv2.imwrite(os.path.join(rgn_out_dir, f"{prefix}_RGN{ext}"), rectified_rgn)
                
        # 3. Process Thermal if it exists
        if os.path.exists(therm_path):
            img_therm = cv2.imread(therm_path, cv2.IMREAD_UNCHANGED)
            if img_therm is not None:
                # Same handling logic as original scripts
                if img_therm.dtype == np.uint16:
                    img_therm = cv2.normalize(img_therm, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                elif len(img_therm.shape) == 3:
                    img_therm = cv2.cvtColor(img_therm, cv2.COLOR_BGR2GRAY)
                    
                rectified_therm = cv2.remap(img_therm, map1_therm, map2_therm, cv2.INTER_LINEAR)
                cv2.imwrite(os.path.join(therm_out_dir, f"{prefix}_Thermal{ext}"), rectified_therm)
                
    print("\nBatch Stereo-Rectification complete!")

if __name__ == "__main__":
    main()
