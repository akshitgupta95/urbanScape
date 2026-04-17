# urbanScape

Code repository for **The Spectrascapes Dataset: Street-view imagery beyond the visible captured using a mobile platform**.

Spectrascapes is an open-access dataset of **17,718 street-level multi-spectral images** (RGB, Near-Infrared, and Thermal) captured across diverse urban morphologies in the Netherlands — from villages to large urban areas. The data was collected on bikes using a custom multi-sensor mobile platform.

---

## Repository Structure

```
urbanScape/
├── UrbanScapesHardware/     # Hardware code for the UrbanScapes capture platform
└── scripts/                 # Python scripts for calibration, metadata enrichment & analysis of the Spectrascapes dataset available on Zenodo.
```

### [`UrbanScapesHardware/`](UrbanScapesHardware/)

Raspberry Pi (or Jetson Nano) code that orchestrates synchronised data capture from:

- **RGB camera** — Pi Camera Module (MIPI CSI-2)
- **MAPIR Survey RGN camera** — controlled via PWM
- **FLIR Lepton thermal camera** — via OpenMV microcontroller (UART/RPC)
- **GPS module** — via `gpsd`

Supports single-capture (short button press) and continuous-capture (long press) modes. See [`UrbanScapesHardware/README.md`](UrbanScapesHardware/README.md) for wiring pinout, startup configuration, and deployment instructions.

### [`scripts/`](scripts/)

Python tooling managed as a [uv](https://docs.astral.sh/uv/) project (Python ≥ 3.12). Contains three modules:

| Directory | Description |
|-----------|-------------|
| `scripts/calibration/` | Intrinsic & extrinsic camera calibration and stereo rectification using OpenCV |
| `scripts/metadata/` | KNMI weather data enrichment and Pleiades Neo satellite tile extraction |
| `scripts/usecases/` | Example analysis — NIR reflectance comparison across building façade materials |

#### Quick start

```bash
cd scripts
uv sync                  # install all dependencies from the lockfile
uv run calibration/calibrate_intrinsics.py
uv run calibration/calibrate_extrinsics.py
```

See [`scripts/README.md`](scripts/README.md) for the full setup guide, dependency table, and per-script documentation.

---

## Citation

If you use the Spectrascapes dataset or this code, please cite:

```bibtex
@article{spectrascapes2026,
  title   = {The Spectrascapes Dataset: Street-view imagery beyond the visible captured using a mobile platform},
  author  = {Gupta, Akshit et. al.},
  journal = {arXiv preprint arXiv:2604.13315},
  year    = {2026}
}
```

---

## License

The code in this repository is licensed under the [MIT License](LICENSE).

```
Copyright (c) 2026 IamAkshitGupta.com
```
