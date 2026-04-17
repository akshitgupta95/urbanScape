import RPi.GPIO as GPIO
from signal import pause
import cv2, os
import time
import threading
from datetime import datetime,timedelta
from captureThermalImages import capture_thermal_image
from captureRGNImages import captureImageAndTransferData
from datasetCreationUtility import setupDirectories
from captureRGBImages import start_camera, stop_camera, capture_image
from gpsLogger import getCurrentLocationAndLogIt

mapir_pin=18
button_pin=2
delta= timedelta(seconds=0)
#lock is used to prevent race condition between button press and release
lock= threading.Lock()

#Steps: 
#       0. setup folders for proper image storage and dataset creation
#       1. log GPS data
#       2. capture thermal image
#       3. save thermal image
#       4. capture RGB image
#       5. capture RGN image
def startCollection():
    # setup dataset collection directory so data is stored there.
    setupDirectories()
    #1. log GPS data
    getCurrentLocationAndLogIt()
    #2. capture thermal image
    thermal_image = capture_thermal_image(debug=False)
    #3. save thermal image in dataset directory
    if thermal_image is not None:
    	cv2.imwrite("thermal_image.jpg", cv2.rotate(thermal_image, cv2.ROTATE_180))
    #4. capture RGB image
    capture_image()
    #5. capture RGN image and transfer it to dataset directory (transfer disabled by default)
    captureImageAndTransferData(mapir_pin)
    #change directory back to original directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

#this button callback function runs on seperate thread than the main program
def buttonPressed(button_pin):
    if GPIO.input(button_pin):
        updateDelta()
    else:
        global timeOfButtonPress
        timeOfButtonPress = datetime.now()

#this function handles the updating of delta variable with thread lock
def updateDelta():
    global timeOfRelease
    timeOfRelease = datetime.now()
    with lock:
        global delta
        delta  = timeOfRelease - timeOfButtonPress

if __name__ == "__main__":
    #this handles the GPIO setup and button event detection with both short press and long press with callback functions.
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(button_pin, GPIO.IN, GPIO.PUD_UP) #add button event detection
        # GPIO.add_event_detect(button_pin, GPIO.FALLING, startCollection, bouncetime=300)
    GPIO.add_event_detect(button_pin, GPIO.BOTH, buttonPressed, bouncetime=100)
    try:
        while True:
            with lock: #prevents callback from updating the global var: delta 
                if delta.total_seconds() > 0.5 and delta.total_seconds() < 5:
                    print("Short Press Detected")
                    delta = timedelta(seconds=0)
                    startCollection()
                elif delta.total_seconds() > 5:
                    print("Long Press Detected")
                    delta = timedelta(seconds=0.515) #any random number will do as it acts as flag after lock is released
            # flag check to continue long press action, as soon as button pressed again, delta value will change
            while delta.total_seconds() == 0.515:
                time.sleep(0.1)
                startCollection()
            #prevents CPU hogging         
            time.sleep(0.1) 
    finally:
        print("Cleaning up GPIO configurations...")
        GPIO.cleanup()
        stop_camera()
