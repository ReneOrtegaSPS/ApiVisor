import json, logging, os

import boto3
from botocore.exceptions import ClientError

import common_funcs as cf


BUCKET = os.environ['BUCKET']


def update_object_to_glacier(s3_key, s3_version_id: str):
    """
    Update the storage class of an object.
    NOTE: To update the class of an object it needs to be copied and pasted with the same key, so it's
    necessary to delete the old version.
    """
    
    s3 = boto3.client('s3')
    copy_source = {
        'Bucket': BUCKET,
        'Key': s3_key
    }
    
    s3.copy(
      copy_source, BUCKET, s3_key,
      ExtraArgs = {
        'StorageClass': 'GLACIER_IR',
        'MetadataDirective': 'COPY'
      }
    )
    
    s3.delete_object(Bucket=BUCKET, Key=s3_key, VersionId=s3_version_id)


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
    
    
    contract_number = body['contract_number']

    s3_client = boto3.client('s3')
    response = s3_client.list_objects_v2(
        Bucket=BUCKET, Prefix=contract_number
    )

    if 'Contents' not in response:
        return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'Contract number not found.'
                })
            }
    
    for file in response['Contents']:
        if file['StorageClass'] in ['GLACIER', 'GLACIER_IR']:
            continue
        metadata_response = cf.key_exists_in_bucket(file['Key'])
        try:
            update_object_to_glacier(file['Key'], metadata_response['VersionId'])
        except ClientError as e:
            print(f'ERROR en operación PATCH: {e.response["Error"]}')
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal Server Error'})
            }
    
        
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Files dismissed succesfully.'})
    }
