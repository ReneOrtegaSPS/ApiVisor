import json, os

import boto3
from botocore.exceptions import ClientError

import common_funcs as cf

BUCKET = os.environ['BUCKET']


def lambda_handler(event, context):
    if 'body' not in event:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': "A body in the request is required."
            })
        }
    
    body = cf.get_body_dict_from_event(event)
    if not body:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': "The body isn't formatted properly."
            })
        }
    
    missing_parameters = cf.missing_parameters_from_file_dict(body, ['contract_number', 'filename'])
    if missing_parameters:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': f'\'{", ".join(missing_parameters)}\' parameter(s) is/are missing.'
            })
        } 
        
    version = body.get('version_id')
    contract_number = body['contract_number']
    filename_no_extension = body['filename'].split('.')[0]
    if not version:
        # si no existe version = false
        if cf.folder_exists_and_not_empty(f"{contract_number}/{filename_no_extension}"):
            version = cf.get_latest_version(contract_number, filename_no_extension)
    
    s3_key = f"{contract_number}/{filename_no_extension}/{version}.txt"
    
    s3_client = boto3.client('s3')
    if not cf.key_exists_in_bucket(s3_key):
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'File not found.'
            })
        }

    try:
        s3_client.delete_object(Bucket=BUCKET, Key=s3_key)
    except ClientError as e:
        print(e.response['Error'])
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': e.response['Error']['Message']
            })
        }
    
    return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'File deleted.'
            })
        }
    