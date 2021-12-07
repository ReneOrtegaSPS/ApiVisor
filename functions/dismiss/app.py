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
    s3_root_key = f"{contract_number}/{filename_no_extension}"
    if version:
        # Solo la version especificada
        s3_key = f"{s3_root_key}/{version}.txt"
        metadata_response = cf.key_exists_in_bucket(s3_key) 
        
        if not metadata_response:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'File not found.'
                })
            }
        
        try:
            update_object_to_glacier(s3_key, metadata_response['VersionId'])
        except ClientError as e:
            error_storage_class = e.response['Error']['StorageClass']
            if error_storage_class == 'GLACIER':
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'The file its already on Glacier Storage'})
                }
            elif error_storage_class == 'GLACIER_IR':
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'The file its already on Glacier Storage IR'})
                }
            
            logging.error(f'ERROR en operación PATCH: {e.response["Error"]}')
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Internal Server Error'})
            }
    else:
        # if version is not provided, all versions will be moved to glacier
        if cf.folder_exists_and_not_empty(s3_root_key):    
            all_versions = cf.get_versions_of_file(contract_number, filename_no_extension)
            for version in all_versions:
                if version['storage_class'] in ['GLACIER', 'GLACIER_IR']:
                    continue

                s3_version_key = f"{s3_root_key}/{version['version_id']}.txt"
                metadata_response = cf.key_exists_in_bucket(s3_version_key)
                try:
                    update_object_to_glacier(s3_version_key, metadata_response['VersionId'])
                except ClientError as e:
                    logging.error(f'ERROR en operación PATCH Multiples archivos:{version["version_id"]} {e.response["Error"]}')
                    print(f'ERROR en operación PATCH Multiples archivos:{version["version_id"]} {e.response["Error"]}')
                    return {
                        'statusCode': 500,
                        'body': json.dumps({'error': 'Internal Server Error'})
                    }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'File not found.'
                })
            }
    
    
        
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'File updated succesfully.'})
    }
