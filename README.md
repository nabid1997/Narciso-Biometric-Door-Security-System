# Narciso-Biometric-Door-Security-System
IoT project
Running the programme
To start the application in Raspberry Pi 4B, Linux CLI Terminal is used with the following commands:
sudo python3 yourfilename.py -e **********-ats.iot.us-east-1.amazonaws.com -r /home/pi/awsiotcore/root-CA.crt -c /home/pi/awsiotcore/RPI4.cert.pem -k /home/pi/awsiotcore/RPI4.private.key.
However, the programme can be also run with sudo python3 yourfilename.py command but won’t work due to missing certificates.
Commands explanation:
•	python3 is the Python version command
•	NH_2252343.py is the python file where the programme is written
•	-e **********-ats.iot.us-east-1.amazonaws.com is the endpoint of the IoT Core Raspberry Pi device
•	-r /home/pi/awsiotcore/root-CA.crt is the path of the rootCA certificate
•	-c /home/pi/awsiotcore/RPI4.cert.pem is the path for the cert,pem certificate 
•	-k /home/pi/awsiotcore/RPI4.private.key is the path for the private key
