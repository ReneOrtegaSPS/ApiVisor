import json, os
from datetime import datetime
from typing import Dict

import boto3

import common_funcs as cf


BUCKET = os.environ['BUCKET']
DATETIME_FORMAT = '%Y%m%d_%H%M%S'


def get_current_file_info(folder: str) -> Dict:
    """
    Returns the current file information.
    """
    s3 = boto3.client('s3')
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=folder, Delimiter='/')
    
    if 'Contents' in resp:
        files = resp['Contents']
        latest_file = max(files, key=lambda x: datetime.strptime(x['Key'].split('/')[-1].replace('.txt', ''), DATETIME_FORMAT))
        is_archived = False
        print(latest_file)
        if latest_file['StorageClass'] in ['GLACIER', 'GLACIER_IR']:
            is_archived = True
        latest_file_formatted = {
            'filename': latest_file['Key'].split('/')[1],
            'size': latest_file['Size'],
            'last_modified': latest_file['LastModified'].strftime('%Y/%m/%d %H:%M%S'),
            'archived': is_archived
        }
        
        return latest_file_formatted

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
    missing_parameters = cf.missing_parameters_from_file_dict(body, ['contract_number'])
    if missing_parameters:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': f'\'{", ".join(missing_parameters)}\' parameter(s) is/are missing.'
            })
        } 
        
    filenames = cf.get_filenames_in_contract_number(body['contract_number'])
    last_version_filenames = []
    if filenames:
        for filename in filenames:
            latest_file = get_current_file_info(filename['Prefix'])
            if latest_file:
                last_version_filenames.append(latest_file)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'filename_items': last_version_filenames
            })
        }
    
    return {
        'statusCode': 404,
        'body': json.dumps({
            'error': 'Contract Number not found.'
        })
    }
