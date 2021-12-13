import json, os
from typing import Dict, List, Union

import boto3
from botocore.exceptions import ClientError

import common_funcs as cf


TEMP_BUCKET = os.environ['TEMP_BUCKET']
DESTINATION_BUCKET = os.environ['BUCKET']
SNS_ARN = os.environ['SNS_ARN']


def send_email_sns(message: str, contract_number: str, filename: str):
    """
    Send email to the emails suscribed to the sns topic
    """
    sns_client = boto3.client('sns')
    sns_client.publish(
        TopicArn=SNS_ARN,
        Message=message,
        Subject=f"{contract_number} - {filename}"
    )

def delete_file_from_temp_bucket(s3_key: str):
    """
    Delete file from Temp bucket
    """
    s3_client = boto3.client('s3')
    s3_client.delete_object(Bucket=TEMP_BUCKET, Key=s3_key) # Elimino archivo bucket temporal

def lambda_handler(event, context):
    s3_event = event['Records'][0]['s3']
    s3_key = s3_event['object']['key']
    
    contract_number, filename, version = s3_key.split('/')
    version = version.split('.')[0]
    
    s3_client = boto3.client('s3')
    temp_response = s3_client.get_object(Bucket=TEMP_BUCKET, Key=s3_key)
    try:        
        json_file = json.loads(temp_response['Body'].read().decode('utf-8'))
    except:
        error_message = f'''
        The filename: {filename} of the contract number: {contract_number} has invalid json format.
        '''
        delete_file_from_temp_bucket(s3_key)
        send_email_sns(error_message, contract_number, filename)
        return
    
    missing_parameters = cf.missing_parameters_from_file_dict(json_file, ['content_type', 'filename', 'file'])
    if missing_parameters:
        print(f'\'{", ".join(missing_parameters)}\' parameter(s) is/are missing.')
        error_message = f"""
        The filename: {filename} of the contract number: {contract_number} 
        has these parameter(s) missing: '{", ".join(missing_parameters)}'
        """
        delete_file_from_temp_bucket(s3_key)
        send_email_sns(error_message, contract_number, filename)
        
        return
        
    
    
    s3_client.put_object(
        Body=json.dumps(json_file), Bucket=DESTINATION_BUCKET, 
        Key=s3_key, Metadata={"encoded_content_type": 'application/json'}
    )
    delete_file_from_temp_bucket(s3_key)
    
    
    print("ENVIO SUCCESFULL")