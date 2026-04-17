# Image script running on openMV as a loop for remote procedure calls (RPC) in UART mode. 
# Rename this file to main.py and place it in the sd card of the OpenMV camera so that is runs automatically on boot.
# Part of the code is based on the default library code from OpenMV Github. Part of it is modified.

#the libraries below are installed in the firmware of OpenMV hardware module. They can be updates by updating the firmware of OpenMV hardware module using OpenMV IDE.
import omv
import rpc
import sensor
import struct
import pyb
import time
from pyb import LED

#these are the min and max temperature in to be detected using the FLIR LEPTON 3.5.
min_temp_in_celsius = 0
max_temp_in_celsius = 40
# Initialize the sensor with the FLIR LEPTON 3.5 thermal camera.
sensor.reset()
sensor.ioctl(sensor.IOCTL_LEPTON_SET_MODE, True)
sensor.ioctl(sensor.IOCTL_LEPTON_SET_RANGE, min_temp_in_celsius, max_temp_in_celsius)
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QQVGA)
sensor.skip_frames(time=2000)

# Turn off the frame buffer connection to the IDE from the OpenMV Cam side.
#
# This needs to be done when manually compressing jpeg images at higher quality
# so that the OpenMV Cam does not try to stream them to the IDE using a fall back
# mechanism if the JPEG image is too large to fit in the IDE JPEG frame buffer on the OpenMV Cam.
omv.disable_fb(True)


# the interface is created as a slave device to the master device (Raspberry Pi).
# uart port is set to 3, which was recommeded by the OpenMV documentation.
interface = rpc.rpc_uart_slave(baudrate=115200, uart_port=3)

# this is for debugging purpose, it will blink on-board LED to white for one second.
LED(2).on()
LED(3).on()
LED(1).on()
time.sleep(1)
LED(2).off()
LED(3).off()
LED(1).off()

################################################################
# Call Backs
################################################################
# When called sets the pixformat and framesize, takes a snapshot
# and then returns the frame buffer jpg size to store the image in.
# data is a pixformat string and framesize string.

# this captures a JPEG image snapshot from the OpenMV camera and blinks the LED 3(Blue) on the OpenMV camera for debugging purpose.
# Don't add time.sleep() in this function, as it cause issues with the RPC interface due to synchronization.
def jpeg_image_snapshot(data):
    LED(3).on()
    pixformat, framesize = bytes(data).decode().split(",")
    sensor.set_pixformat(eval(pixformat))
    sensor.set_framesize(eval(framesize))
    img = sensor.snapshot()
    img.to_jpeg(quality=100)
    LED(3).off()
    return struct.pack("<I", img.size())


def jpeg_image_read_cb():
    interface.put_bytes(sensor.get_fb().bytearray(), 5000)  # timeout

# Read data from the frame buffer given a offset and size.
# If data is empty then a transfer is scheduled after the RPC call finishes.
# data is a 4 byte size and 4 byte offset.
def jpeg_image_read(data):
    if not len(data):
        interface.schedule_callback(jpeg_image_read_cb)
        return bytes()
    else:
        offset, size = struct.unpack("<II", data)
        return memoryview(sensor.get_fb().bytearray())[offset : offset + size]


# Register call backs.

interface.register_callback(jpeg_image_snapshot)
interface.register_callback(jpeg_image_read)

# Once all call backs have been registered we can start
# processing remote events. interface.loop() does not return and runs forever on the OpenMV Cam.

interface.loop()
