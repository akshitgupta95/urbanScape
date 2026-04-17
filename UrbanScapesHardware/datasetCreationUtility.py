import os, random
from datetime import datetime
import pickle

def setupDirectories():
    # Path Configuration for dataset
    specificPath = datetime.today().strftime("%Y-%m-%d-%H")
    datasetsDir = os.path.join('..', "datasets")
    if not os.path.isdir(datasetsDir):
        os.mkdir(os.path.join('..',"datasets"))
    if not specificPath in os.getcwd():
        try:
            os.chdir(os.path.join("../datasets", specificPath))
        except:
            os.mkdir(os.path.join("../datasets", specificPath))
            os.chdir(os.path.join("../datasets", specificPath))

    currentLocationNumber = load_Location_number("data.pickle")
    if currentLocationNumber == None:
        currentLocationNumber = 1
    directoryName = "Location" + str(currentLocationNumber)
    save_Location_number(currentLocationNumber + 1)
    try:
        os.mkdir(directoryName)
        os.chdir(directoryName)
    except OSError as error:
        # The file exists already, so push data to error folders
        print(error)
        filePath = "FileAlreadyExistsError" + str(random.randint(0, 100))
        os.mkdir(filePath)
        os.chdir(filePath)
    print("Data will be stored in" + os.getcwd())

def save_Location_number(LocationNumber):
    try:
        with open("data.pickle", "wb") as f:
            pickle.dump(LocationNumber, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as ex:
        print("Error during pickling object (Possibly unsupported):", ex)

def load_Location_number(filename):
    try:
        with open(filename, "rb") as f:
            return pickle.load(f)
    except Exception as ex:
        print("Error during unpickling object (Possibly unsupported):", ex)
