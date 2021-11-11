#Libraries
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import sys
import logging
import time
import getopt
from datetime import datetime
import picamera
import os
import tinys3
import json
from signal import signal, SIGTERM, SIGHUP, pause
from rpi_lcd import LCD
from time import sleep
import board 
import busio as io
import adafruit_mlx90614 as sensor
import RPi.GPIO as GPIO

#LCD setup
lcd = LCD()

Instructions = """Instructions:

Type python yourfilename.py -e <IoTendpoint> -r <rootCSourceA> -c <certSource> -k <privateKeySource>
to initialise and authenticate to AWS IoT Core

Type "python yourfilename.py -h" for help.
"""
# Help 
Help = """-e, --IoTendpoint
-r, --rootCA
	Root CA 
-c, --cert
	Certificate 
-k, --key
	Private key 
-h, --help

"""
# Read in CLI parameters
host = "your IoT Core device enpoint"
rootCASource = "/home/pi/awsiotcore/root-CA.crt"
certificateSource = "/home/pi/awsiotcore/RPI4.cert.pem"
privateKeySource = "/home/pi/awsiotcore/RPI4.private.key"
try:
	opts, args = getopt.getopt(sys.argv[1:], "hwe:k:c:r:", ["help", "endpoint=", "key=","cert=","rootCA="])
	if len(opts) == 0:
		raise getopt.GetoptError("Input parameters missing!")
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			print(helpInfo)
			exit(0)
		if opt in ("-e", "--endpoint"):
			host = arg
		if opt in ("-r", "--rootCA"):
			rootCASource = arg
		if opt in ("-c", "--cert"):
			certificateSource = arg
		if opt in ("-k", "--key"):
			privateKeySource = arg
except getopt.GetoptError:
	print(Instructions)
	exit(1)

# Notification if there's missing configuration
configMissing = False
if not host:
	print("Missing '--endpoint'")
	configMissing = True
if not rootCASource:
	print("Missing '--rootCA'")
	configMissing = True
if not certificateSource:
    print("Missing '--cert'")
    configMissing = True
if not privateKeySource:
    print("Missing '--key'")
    configMissing = True
if configMissing:
	exit(2)

#relay setup
global doorStatus
doorStatus=False
#This means we will refer to the GPIO pins
GPIO.setmode(GPIO.BCM)
#This sets up the GPIO 24 pin as an output pin
GPIO.setup(24, GPIO.OUT)

# Properties for snapshots
image_width = 800
image_height = 480
file_type = '.jpg'

#Infrared heat sensor setup.
i2c = io.I2C(board.SCL, board.SDA, frequency=100000)
mlx = sensor.MLX90614(i2c)
body_temp = round(mlx.object_temperature)
ambient_temp = round(mlx.ambient_temperature)

#AWS S3 authentication properties
access_key_id = ''
secret_access_key = ''
bucket_name = 'your bucketname'
    
# Character Map for USB RFID Device
hid = { 4: 'a', 5: 'b', 6: 'c', 7: 'd', 8: 'e', 9: 'f', 10: 'g', 11: 'h', 12: 'i', 13: 'j', 14: 'k', 15: 'l', 16: 'm', 17: 'n', 18: 'o', 19: 'p', 20: 'q', 21: 'r', 22: 's', 23: 't', 24: 'u', 25: 'v', 26: 'w', 27: 'x', 28: 'y', 29: 'z', 30: '1', 31: '2', 32: '3', 33: '4', 34: '5', 35: '6', 36: '7', 37: '8', 38: '9', 39: '0', 44: ' ', 45: '-', 46: '=', 47: '[', 48: ']', 49: '\\', 51: ';' , 52: '\'', 53: '~', 54: ',', 55: '.', 56: '/'  }
hid2 = { 4: 'A', 5: 'B', 6: 'C', 7: 'D', 8: 'E', 9: 'F', 10: 'G', 11: 'H', 12: 'I', 13: 'J', 14: 'K', 15: 'L', 16: 'M', 17: 'N', 18: 'O', 19: 'P', 20: 'Q', 21: 'R', 22: 'S', 23: 'T', 24: 'U', 25: 'V', 26: 'W', 27: 'X', 28: 'Y', 29: 'Z', 30: '!', 31: '@', 32: '#', 33: '$', 34: '%', 35: '^', 36: '&', 37: '*', 38: '(', 39: ')', 44: ' ', 45: '_', 46: '+', 47: '{', 48: '}', 49: '|', 51: ':' , 52: '"', 53: '~', 54: '<', 55: '>', 56: '?'  }
# logging configuration
logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# Initialisation for AWSIoTMQTTClient
myAWSIoTMQTTClient = None

myAWSIoTMQTTClient = AWSIoTMQTTClient("myProject")
myAWSIoTMQTTClient.configureEndpoint(host, 8883)
myAWSIoTMQTTClient.configureCredentials(rootCASource, privateKeySource, certificateSource)

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 31, 19)
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  
myAWSIoTMQTTClient.configureDrainingFrequency(2) 
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(11)  
myAWSIoTMQTTClient.configureMQTTOperationTimeout(6)  

# PiCamera setup
picamera = picamera.PiCamera()
picamera.resolution = (image_width, image_height)
picamera.awb_mode = 'auto'

#function to control the relay
def controlRelay():
    lcd.text("Door is", 1)
    lcd.text("open...", 2)
    GPIO.output(24, 0)
    sleep(5)
    print("Door is open...")
    sleep(4)
    
    
    GPIO.output(24, 1)
    print("Door is closing...")
    sleep(2)
    lcd.text("Door is", 1)
    lcd.text("closing...", 2)
    sleep(2)
    

# Starts the RFiD 
rfidDevice = open('/dev/hidraw0', 'rb')
#function to capture RFiD scan
def scanInput():
    rfid = ""
    shift = False
    done = False
    while not done:
       buffer = rfidDevice.read(8)
       for c in buffer:
          if c > 0:
             if int(c) == 40:
                done = True
                break;
             if shift:
                if int(c) == 2 :
                   shift = True
                else:
                   rfid += hid2[ int (c) ]
                   shift = False
             else:
                if int(c) == 2 :
                   shift = True
                else:
                   rfid += hid[ int(c) ]
    return rfid

#function to get body temperature
def checkBodyTemp():
    if (body_temp) >= 20 and (body_temp) <= 35:
      print("Acceptable body temperature"+ str(body_temp)+"°C")
      lcd.text("Acceptable body temperature:"+ str(body_temp)+"°C", 1)
      sleep(3)
      return True
    elif (body_temp) >= 35:
      lcd.text("Temp high, call security:"+ str(body_temp)+"°C", 1)
      print(str(body_temp)+ "°C"+"Temperature too high call security")
      sleep(3)
      return False
    elif (body_temp) <= 19:
      lcd.text("Inaccurate scan,", 1)
      lcd.text("Come closer!", 2)
      print("Inaccurate scan. Come closer!" + str(body_temp)+"°C")
      sleep(3)
      return False
#function to upload the snapshot to S3
def S3Upload(filename):
    file_source = filename + file_type
    picamera.capture(file_source)
    conn = tinys3.Connection(access_key_id, secret_access_key)
    file_open = open(file_source, 'rb')
    conn.upload(file_source, file_open, bucket_name,
               headers={
               'x-amz-meta-cache-control': 'max-age=60'
               })
    if os.path.exists(file_source):
        os.remove(file_source)

#MQTT message callback for Rekognition result

def rekognitionCallback(client, userdata, message):
    print("Got a new message: ",message)
    global doorStatus
    data = json.loads(message.payload)
    print("test",data)
    try:
        similarity = data[1][0]['Similarity']
        print("Similarity Percentage: " + str(similarity))
       
        if(similarity >= 90):
            doorStatus=True
            print("Face recognition successful.")
            lcd.text("FaceID", 1)
            lcd.text("similarity:" + str(similarity), 2)
            sleep(2)
        elif(similarity <= 89):
            print("Access denied, bad face ID.")
            lcd.text("Access denied", 1)
            lcd.text("bad face ID.", 2)
            sleep(2)
    except Exception as e:
        print("We hit exception",e)
        pass
    print("Event finished.") 


#function for RFID input number
def RFIDNumberCheck(rfidnumber):
    RFIDnumberIndex = ['0002783957', '0002409034', '0002408216']
    match = True
    if rfidnumber in RFIDnumberIndex:
        return True
    else:
        return False
    
# Connection and subscribption to AWS IoT Core similarity topic
myAWSIoTMQTTClient.connect()
myAWSIoTMQTTClient.subscribe("rekognition/similarity", 1, rekognitionCallback)
time.sleep(6)

## Infinite loop

#Welcome text
while True:
    lcd.text("Welcome to", 1)
    lcd.text("our building!", 2)
    sleep(4)
    lcd.text("Please scan", 1)
    lcd.text("your Badge", 2)
    sleep(3)
    print("Please Scan your Badge...")
    
    #scanInput function becomes a variable
    scanRFiD = scanInput()
    
    print(scanRFiD)
    
    #Validating ID badge
    if(RFIDNumberCheck(scanRFiD)):
        print("RFID Scan Accepted, checking body temperature...")
        lcd.text("Valid scan,", 1)
        lcd.text("checking temp.", 2)
        sleep(6)
    
    #Validating body temperature
        if checkBodyTemp():
            
    #Taking picture and uploading to the cloud if conditions are passed
            S3Upload(scanRFiD)
            sleep(3)
            print(doorStatus)
            if doorStatus:
                controlRelay()
                
    #Text if ID badge invalid
    else:
        print("RFID Scan Declined - Access Denied ==> Retry")
        lcd.text("Scan declined,", 1)
        lcd.text("retry...", 2)
        sleep(5)


