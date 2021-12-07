import json, os

import boto3

import common_funcs as cf


BUCKET = os.environ['BUCKET']
BUCKET_TEMP = os.environ['BUCKET_TEMP']
MAX_MB_SIZE_ALLOWED = os.environ.get('MAX_MB_SIZE', 100)

def lambda_handler(event, context):
    if 'body' not in event:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': "A body in the request is required."
            })
        }
        
    body = cf.get_body_dict_from_event(event)
    
    missing_parameters = cf.missing_parameters_from_file_dict(body, ['contract_number', 'filename'])
    if missing_parameters:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': f'\'{", ".join(missing_parameters)}\' parameter(s) is/are missing.'
            })
        }
        
    filename_no_extension = body['filename'].split('.')[0]
    if '/' in filename_no_extension:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': "A filename cant have '/' on it."
            })
        }
        
    contract_number = body['contract_number']
    root_folder_s3 = f"{contract_number}/{filename_no_extension}"
        
    s3_key = cf.get_new_s3_key(root_folder_s3)
        
    s3_client = boto3.client('s3')
    response = s3_client.generate_presigned_post(BUCKET_TEMP, s3_key, 
            Conditions=[["content-length-range", 1, MAX_MB_SIZE_ALLOWED * 1048576]], # 100mb
            ExpiresIn=300)
        
        
    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
