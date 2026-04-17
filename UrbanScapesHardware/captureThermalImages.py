import io, rpc, struct, cv2, numpy as np

# This script captures thermal images from a remote device using RPC over UART.
# keep rpc module in the same directory as this script. This is old RPC custom library of OpenMV camera. With newer RPC library, changes are required.

# Make sure to have the OpenMV camera connected to the correct UART port of pi, GPIO on Pi for UART.
# Create interface to the OpenMV camera using RPC over UART.
interface = rpc.rpc_uart_master(baudrate=115200, port="/dev/ttyS0")
print("Connection successful!")

def get_frame_buffer_call_back(pixformat_str, framesize_str, cutthrough, silent):
    if not silent:
        print("Getting Remote Frame...")
    # Call the remote procedure on OpenMV to get a JPEG image snapshot. 2 arguments are passed in bytes.
    result = interface.call("jpeg_image_snapshot", "%s,%s" % (pixformat_str, framesize_str))
    if not silent:
        print(type(result))
        print(len(result))

    if result is not None:
        # Below code is based on the code running on OpenMV. See openMVCode.py for more details.
        size = struct.unpack("<I", result)[0]
        img = bytearray(size)

        if cutthrough:
            # Fast cutthrough data transfer with no error checking.
            # Before starting the cut through data transfer we need to sync both the master and the
            # slave device. On return both devices are in sync.
            result = interface.call("jpeg_image_read")
            if result is not None:
                # GET BYTES NEEDS TO EXECUTE NEXT IMMEDIATELY WITH LITTLE DELAY NEXT.
                # Read all the image data in one very large transfer.
                interface.get_bytes(img, 5000)  # timeout

        else:
            # Slower data transfer with error checking.
            # Transfer 32 KB chunks.
            chunk_size = 1 << 15

            if not silent:
                print("Reading %d bytes..." % size)
            for i in range(0, size, chunk_size):
                ok = False
                for j in range(3):  # Try up to 3 times.
                    result = interface.call(
                        "jpeg_image_read", struct.pack("<II", i, chunk_size)
                    )
                    if result is not None:
                        img[i : i + chunk_size] = result  # Write the image data.
                        if not silent:
                            print("%.2f%%" % ((i * 100) / size))
                        ok = True
                        break
                    if not silent:
                        print("Retrying... %d/2" % (j + 1))
                if not ok:
                    if not silent:
                        print("Error!")
                    return None

        return img

    else:
        if not silent:
            print("Failed to get Remote Frame!")

    return None

# Debug = True to show the image on the screen, False to just return the image.
def capture_thermal_image(debug: False):

    # When cutthrough is False the image will be transferred through the RPC library with CRC and
    # retry protection on all data moved. For faster data transfer set cutthrough to True so that
    # get_bytes() and put_bytes() are called after an RPC call completes to transfer data
    # more quicly from one image buffer to another. Note: This works because once an RPC call
    # completes successfully both the master and slave devices are synchronized completely.

    # QQVGA is resolution of FLIR LEPTON 3.5
    img = get_frame_buffer_call_back(
        "sensor.GRAYSCALE", "sensor.QQVGA", cutthrough=True, silent= True
    )

    if img is not None:
        try:
            file_bytes = np.frombuffer(io.BytesIO(img).read(), dtype=np.uint8)
            img_cv = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
            if debug:
                cv2.imshow("thermal image", img_cv)
                cv2.waitKey()
            return img_cv

        except BaseException:
            pass

if __name__ == "__main__":
    thermal_image = capture_thermal_image(debug=True)
    cv2.imwrite("thermal_image.jpg", thermal_image)