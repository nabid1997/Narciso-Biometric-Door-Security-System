from __future__ import print_function
import boto3
from decimal import Decimal
import json
import urllib
import os

print('Function Loading')


iot = boto3.client('iot-data')

region='us-east-1'
rekognition = boto3.client("rekognition", region)

#Helper Function calling Rekognition API
def compare_faces(bucket, key, key_target):
   print ("bucket is =",bucket)
   print("key is ",key)
   print("target is",key_target)
   bucket='myemployeesource'
   response = rekognition.compare_faces(
	    SourceImage={
	         
	         "S3Object": {
				"Bucket": bucket,
				"Name": key,
			}
		},
		TargetImage={
		     
		     "S3Object": {
				"Bucket": bucket,
				"Name": key_target,
			}
		},
	    SimilarityThreshold=90,
	    QualityFilter='AUTO'

	)
   return response['SourceImageFace'], response['FaceMatches']

#Main handler


def lambda_handler(event, context):
   
    print("Received event: " + json.dumps(event, indent=2))
    
    
    
    bucket = event['Records'][0]['s3']['bucket']['name']
    print(bucket)
    key = urllib.parse.unquote_plus(str(event['Records'][0]['s3']['object']['key']))
    
    print(key)
    
    key_target = "target/" + key
   
    try:
        response = compare_faces(bucket, key, key_target)
        print(response)
        
        mypayload = json.dumps(response)
        iotResponse = iot.publish(
            topic="rekognition/simi",
            qos=1,
            payload=mypayload)
        print(iotResponse)
        return iotResponse
    except Exception as e:
        print(e)
        print("Error processing object {} from bucket {}. ".format(key, bucket) +
              "Make sure your object and bucket exist and your bucket is in the same region as this function.")
        raise e