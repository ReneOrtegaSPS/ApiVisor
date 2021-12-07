import json, os

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
    contract_number = body['contract_number']
    filename_no_extension = body['filename'].split('.')[0]
    versions = cf.get_versions_of_file(contract_number, filename_no_extension)
    
    if versions:
        return {
        'statusCode': 200,
        'body': json.dumps({'versions': versions})
    }    
    
    return {
        'statusCode': 404,
        'body': json.dumps({'error': 'Filename not found.'})
    }
