# Camera Calibration Tools

This directory contains the necessary tools to perform intrinsic and extrinsic (stereo) camera calibrations for the RGB, RGN, and Thermal camera setups.

These tools read the downloaded calibration dataset and output the generated calibration models into `intrinsics.json` and `extrinsics.json` exactly where the system expects them.

## Requirements

Ensure that you have your environment set up with OpenCV and NumPy.

```bash
uv add opencv-python numpy matplotlib
```

## Usage

Before running the scripts, you can override the dataset location by editing the `DATASET_PATH` variable at the top of each script to point to the base directory of where the zenodo `dataset` was downloaded or cloned.

### 1. Calibrate Intrinsics
First, run the intrinsic script to calibrate all independent cameras and export their metrics independently. This script reads individual images out of the `instrinsic_target` folders.
```bash
uv run calibrate_intrinsics.py
```
This produces `dataset/calibration/intrinsics.json`.

### 2. Calibrate Extrinsics
After generating intrinsics, run the extrinsics cross-mapping to associate the coordinate origins (using RGB as camera 1) for your RGN and Thermal pairs.
```bash
uv run calibrate_extrinsics.py
```
This produces `dataset/calibration/extrinsics.json`.

### 3. Stereo Rectification (Starter Code)
We provide `rectify_dataset_starter.py` as a starter script to loop through the dataset (`dataset/image_data/<city>`) and output stereo-rectified images using your calibration matrices. 
*Note:* This script uses pairwise rectification with RGB as the origin. Because it aligns RGN and Thermal independently to RGB, the Thermal and RGN images will not be perfectly epipolar-aligned to each other. Use this as a foundation for more advanced registration routines.
```bash
uv run rectify_dataset_starter.py
```

## Notes on the Data
- Expected structures include: `dataset/calibration/calibration_plates/instrinsic_target` and `dataset/calibration/calibration_plates/extrinsic_target_pairs`.
- The `SQUARE_SIZE` parameter inside scripts is permanently locked to 0.022 meters (22mm).
- High-contrast Thermal and RGN inversion mechanisms exist natively inside `calibrate_extrinsics.py` to offset specific chessboard material reflection features. You do not need to manually invert anything.
