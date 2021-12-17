import json, logging, os

import boto3

import common_funcs as cf

BUCKET = os.environ['BUCKET']
logger = logging.getLogger()
logger.setLevel(logging.WARNING)


def lambda_handler(event, context):
    if 'body' not in event or event['body'] == '':
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': "A body in the request is required."
            })
        }
    
    
    header_content_type = event['headers'].get('content-type', '')
    if not(header_content_type == 'application/json' or  header_content_type.startswith('multipart/form-data')):
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': "Request Content Type Headers must be 'application/json' or 'multipart/form-data'"
            })
        }
        
    
    
    file_dict = cf.get_file_dict_from_event(event)
    
    missing_parameters = cf.missing_parameters_from_file_dict(file_dict)
    if missing_parameters:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': f'\'{", ".join(missing_parameters)}\' parameter(s) is/are missing.'
            })
        }
        
    filename_no_extension = file_dict['filename'].split('.')[0]
    if '/' in filename_no_extension:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': "A filename cant have '/' on it."
            })
        }
    contract_number = file_dict['contract_number']
    root_folder_s3 = f"{contract_number}/{filename_no_extension}"
    
    if cf.folder_exists_and_not_empty(root_folder_s3):
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'A filename already exists in that contract_number.'
            })
        }
    
    
    s3_key = cf.get_new_s3_key(root_folder_s3)
    file_encoded = json.dumps(file_dict)
    s3 = boto3.resource('s3')
    s3.Object(BUCKET, s3_key).put(Body=file_encoded, Metadata={"encoded_content_type": 'application/json'})
    
    
    return {
        'statusCode': 201,
        'body': json.dumps({
            'message': 'File created.'
        })
    }
