import json, os

import boto3

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
    metadata_response = cf.key_exists_in_bucket(s3_key)
    
    if metadata_response:
        if metadata_response.get('StorageClass') == 'GLACIER':
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'mensaje': 'File is in Glacier Storage, you must restore it first.'
                })
            }
        
        if metadata_response['ContentLength'] >= 6290000: # 6291456 -> 6mb
            s3 = boto3.client('s3')
            presigned_url_response = s3.generate_presigned_url('get_object', Params={
                'Bucket': BUCKET, 'Key': s3_key
            }, ExpiresIn=300)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'presigned_url': presigned_url_response
                })
            }
    
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=BUCKET, Key=s3_key)
            
        json_file = json.loads(response['Body'].read().decode('utf-8'))
        filename = json_file['filename']
        content_type = json_file['content_type']
        encoded_file = json_file['file']
        
        return {
                'statusCode': 200,
                'body': json.dumps({
                    'content_type': content_type,
                    'filename': filename,
                    'encoded_file': encoded_file
                }),
                'isBase64Encoded': False
            }
    
    return {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'File not found.'
            })
        }
