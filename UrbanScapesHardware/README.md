# UrbanScapes Hardware

This repository contains the hardware code for the UrbanScapes, designed to run on a Raspberry Pi or any Linix based general-purpose computer such as Nvidia Jetson Nano. 

The system synchronizes data collection from multiple sensors including an RGB camera, MAPIR survey RGN camera, FLIR Lepton thermal camera (via OpenMV), and a GPS module.

## Setup & Startup
To run the data capture automatically on your Raspberry Pi on startup (`main.py`), you can use one of the following methods:

### 1. Using systemd (Recommended)
This is the most robust way to start processes on boot and keeps logs.
Create a service file at `/etc/systemd/system/urbanscapes.service`:
```ini
[Unit]
Description=UrbanScapes Hardware
After=network.target

[Service]
ExecStart=/usr/bin/python3 /absolute/path/to/UrbanScapesHardware/main.py
WorkingDirectory=/absolute/path/to/UrbanScapesHardware
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi (Replace with your username)

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl enable urbanscapes.service
sudo systemctl start urbanscapes.service
```

### 2. Using crontab
Add a start command to your reboot cron triggers. Open crontab with `crontab -e` and add:
```bash
@reboot cd /absolute/path/to/UrbanScapesHardware && /usr/bin/python3 main.py &
```

*(Note: Replace `/absolute/path/to/` with the actual path to your clone of this repository, e.g., `/home/pi/`).*

## Features & Subsystems

- **Data Capture Button**:
  - **Single Instance Mode (Short Press)**: Pressing the hardware button for 0.5s to 5s triggers a single data capture sequence across all connected sensors.
  - **Continuous Data Capture Mode (Long Press)**: Pressing and holding the button for more than 5s puts the system into continuous data capture until interrupted.
  
- **OpenMV Microcontroller (`CodeForOpenMV` directory)**: 
  This directory contains the MicroPython code (`openMVCodeForLepton.py` / `rpc.py`) that must be uploaded to the OpenMV microcontroller. It configures the OpenMV to be controlled via RPC over UART, allowing the Raspberry Pi to communicate with it and capture thermal imagery.

- **MAPIR Survey RGN Camera**: 
  The MAPIR camera is controlled dynamically using PWM signals sent from the Raspberry Pi over the designated `MAPIR Pin`.

- **RGB Camera**: 
  The primary RGB camera communicates over I2C and MIPI CSI-2. It utilizes the dedicated Pi Camera Port (via ribbon cable) for control and image transfer.

## Hardware Configuration Variables

Before deploying the code, you must configure the following pin variables according to your wiring setup (found primarily in `main.py` and `captureRGNImages.py`):

- `button_pin = 2`: The GPIO pin for the data collection trigger button.
- `mapir_pin = 18`: The GPIO pin used to output PWM control signals to the MAPIR survey camera.

**Additional configuration points:**
- The FLIR Thermal interface (`captureThermalImages.py`) assumes the OpenMV is connected over the Pi's UART port `/dev/ttyS0` with a baudrate of `115200`.
- The GPS logger relies on the standard `gpsd` service being active and broadcasting locally.

## Pinout Map

Connect your modules to the Raspberry Pi according to the following mapping:

| RPi Pin | Matching Pin | Connection Purpose |
| :--- | :--- | :--- |
| **3V3 Power** | GPS: VIN | Power for GPS |
| **Ground** | GPS: GND | GPS Ground |
| **GPIO 4 (GPCLK0)** | GPS: RX | Serial to GPS |
| **GPIO 5** | GPS: TX | Serial from GPS |
| **5V power** | OpenMV: VIN | Power for OpenMV |
| **Pin 6: Ground** | OpenMV: GND | OpenMV Ground |
| **GPIO 14 (TXD)** | OpenMV: P5 | UART RX on OpenMV |
| **GPIO 15 (RXD)** | OpenMV: P4 | UART TX on OpenMV |
| **GPIO 18** | Survey3 HDMI PWM Trigger: white | PWM Trigger for MAPIR |
| **Ground** | Survey3 HDMI PWM Trigger: black | PWM Trigger for MAPIR: Ground |
| **GPIO 2 (SDA)** | On Data Capture Button | Data Collection Trigger for Button |
| **MIPI Camera Serial Interface** | Pi camera module ribbon | RGB camera |
| **Ground** | On Data Capture Button | Ground terminal for Button |

