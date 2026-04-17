import time
from picamera2 import Picamera2
from libcamera import Transform

# Initialize the camera
picam2 = Picamera2()
# Configure for still capture and save the image

"""Configures and starts the camera hardware."""
print("Starting camera...")
transform=Transform(hflip=True,vflip=True)
config = picam2.create_still_configuration(transform=transform)
picam2.configure(config)
picam2.start()
print("Camera started and is ready.")
    # Allow time for auto-algorithms to settle
time.sleep(2)
metadata = picam2.capture_metadata()
    # Now, disable the auto-exposure and auto-white-balance and apply the settled values
shutter_speed_us=4000
picam2.set_controls({
    "AeEnable": False,
    "AwbEnable": False,
    "ExposureTime": shutter_speed_us,
    "AnalogueGain": metadata["AnalogueGain"]
    })
print("Camera settings locked for consistency.")
time.sleep(1) # Give it a moment to apply the settings

def start_camera():
    print("Starting camera...")
    config = picam2.create_still_configuration()
    picam2.configure(config)
    picam2.start()
    print("Camera started and is ready.")
    # Allow time for auto-algorithms to settle
    time.sleep(2)
    metadata = picam2.capture_metadata()
    # Now, disable the auto-exposure and auto-white-balance and apply the settled values
    picam2.set_controls({
        "AeEnable": False,
        "AwbEnable": False,
        "ExposureTime": metadata["ExposureTime"],
        "AnalogueGain": metadata["AnalogueGain"]
    })
    print("Camera settings locked for consistency.")
    time.sleep(1) # Give it a moment to apply the settings

def stop_camera():
    """Stops the camera hardware."""
    picam2.stop()

def capture_image():
    """Captures an image from the camera."""
    picam2.capture_file("RGB.jpg")
