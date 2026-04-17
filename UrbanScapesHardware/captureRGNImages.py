import sys
import numpy as np
import os
from signal import pause
import time
import RPi.GPIO as GPIO
import shutil, glob, cv2 #for dataTransferOnly

def captureImageAndTransferData(out_pin):
    print("Trigger")
    GPIO.setup(out_pin, GPIO.OUT)
    GPIO.output(out_pin, GPIO.HIGH)
    time.sleep(0.001)
    GPIO.output(out_pin, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(out_pin, GPIO.HIGH)
    time.sleep(0.002)
    GPIO.output(out_pin, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(out_pin, GPIO.HIGH)
    time.sleep(0.001)
    GPIO.output(out_pin, GPIO.LOW)
    print("image Captured Succesfully")
    time.sleep(3) #var= time delay based on 1 second + mapir_survey_3W data sheet specs
    #uncomment the line below when you want to transfer data (will add delay)
    #mountAndUnmountSD(out_pin) 
    
#this function handles the mounting and unmounting of SD card
#adds delay due to toggling of modes of camera between image capture and data transfer
def mountAndUnmountSD(out_pin):
    changeMode(out_pin)
    time.sleep(2) #time for mounting SD
    print("SD Mounted")
    transfer_rgn_image()
    time.sleep(3) #var = time needed to transfer data
    print("data transferred")
    changeMode(out_pin)
    time.sleep(1) #var = time delay to go back to image capture mode
    print("SD Un-mounted") 
    
#this function toggles the mode of the camera from image capture to data trasnfer mode and vice versa
#adds delay
def changeMode(out_pin):
    GPIO.output(out_pin, GPIO.HIGH)
    time.sleep(0.001)
    GPIO.output(out_pin, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(out_pin, GPIO.HIGH)
    time.sleep(0.0015)
    GPIO.output(out_pin, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(out_pin, GPIO.HIGH)
    time.sleep(0.001)
    GPIO.output(out_pin, GPIO.LOW)
    time.sleep(0.5)  #var = time delay to listen again to PWM signals

#this function transfers the rgn image from the SD card to the dataset directory
def transfer_rgn_image():
    #this is the path to the SD card where images are stored (change if needed)
    inputPath = "/media/rider/0000-0001/DCIM/Photo/*"
    list_of_files = glob.glob(inputPath)
    try:
        latest_file = max(list_of_files, key=os.path.getctime)
    except:
        print("error occured in rgn image transfer")
        os.chdir("../")
    shutil.copy2(latest_file, os.path.join(os.getcwd(), "rgn.RAW"))
    # return cv2.imread("rgn.jpg")
    
if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    #MAPIR camera PWM signals pin
    out_pin= 18 # the white wire is connected to GPIO 18 (pin 12 pn RPi) 
    while True:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(out_pin, GPIO.OUT)
        #triggering the camera to capture image, data transfer disabled for now
        captureImageAndTransferData(out_pin)
