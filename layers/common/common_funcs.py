import os, json, base64, re
from datetime import datetime
from typing import Dict, List, Union

import boto3
from botocore.exceptions import ClientError
from requests_toolbelt.multipart import decoder

BUCKET = os.environ['BUCKET']
DATETIME_FORMAT = '%Y%m%d_%H%M%S'


# CREATE - UPDATE FILES
def decode_dict(d: Dict) -> Dict:
    """
    Decodes a dictionary with bytes as keys/values
    """
    decoded_dict = {}
    for key, value in d.items():
        if isinstance(key, bytes):
            key = key.decode()
        if isinstance(value, bytes):
            value = value.decode()
        elif isinstance(value, dict):
            value = decode_dict(value)
        decoded_dict.update({key: value})
    return decoded_dict

def get_multipart_key(string: str, key: str) -> str:
    """
    Searchs and returns a value inside a multipart key (key=value)
    """
    regex = f'({key}=)"([^"]*)"'
    value = re.search(regex, string)
    
    return value.groups()[1]

def get_file_dict_from_multipart_body(encoded_body: bytes, content_type: str) -> Dict:
    """
    Obtains a dictionary with all the data from a multipart body. 
    """
    # Get all the parts from the multipart encoded body
    multi_part = decoder.MultipartDecoder(encoded_body, content_type).parts
    file_dict = {}
    for part in multi_part:
        # Get the header dictionary decoded
        decoded_headers = decode_dict(part.headers)
        # Get the value of multipart key 'name'
        multipart_key = get_multipart_key(decoded_headers['Content-Disposition'], 'name')
        
        if multipart_key == 'file':
            # If the part value is the file, get all the information from it
            filename = get_multipart_key(decoded_headers['Content-Disposition'], 'filename')
            file_dict['filename'] = filename
            file_dict['content_type'] = decoded_headers['Content-Type']
            file_dict[multipart_key] = base64.b64encode(part.content).decode()
        else:
            file_dict[multipart_key] = part.content.decode()
            
    return file_dict

def get_file_dict_from_event(event: Dict) -> Dict:
    """
    Get the dictionary inside the body of the request.
    The request body can either be a json or a multipart body.
    """
    if event['isBase64Encoded']:
        body = base64.b64decode(event['body'])
    else:
        body = event['body']
        
    try:
        file_dict = json.loads(body)
    except:
        file_dict = get_file_dict_from_multipart_body(body, event['headers']['content-type'])
        
    return file_dict

# ---

def get_new_s3_key(root_folder_s3: str) -> str:
    """
    Returns a new s3 key version, based on the root folder and the current time
    (which is composed by the contract and the filename.)
    """
    version = datetime.now().strftime(DATETIME_FORMAT)

    s3_key = f"{root_folder_s3}/{version}.txt"
    return s3_key

def get_body_dict_from_event(event: Dict) -> Union[Dict, bool]:
    """
    Get the dictionary of the request body.
    """
    if event['isBase64Encoded']:
        body = base64.b64decode(event['body'])
    else:
        body = event['body']
        
    try:
        body_dict = json.loads(body)
    except:
        return False
        
    return body_dict

def missing_parameters_from_file_dict(file_dict: Dict, req_params: List=['file', 'contract_number', 'filename', 'content_type']) -> List:
    """
    Checks if the file dictionary has missing required parameters and returns them.
    """
    missing_parameters = []
    for req_param in req_params:
        if req_param not in file_dict:
            missing_parameters.append(req_param)
    return missing_parameters

def folder_exists_and_not_empty(path:str) -> bool:
    """
    Check that a folder exists and is not empty
    """
    s3 = boto3.client('s3')
    if not path.endswith('/'):
        path = path + '/' 
    resp = s3.list_objects(Bucket=BUCKET, Prefix=path, Delimiter='/', MaxKeys=1)
    return 'Contents' in resp

def get_versions_of_file(contract_number: str, filename: str, max_index: bool=False) -> List:
    """
    Return all the versions of an object.
    """
    s3_client = boto3.client('s3')
    prefix = f"{contract_number}/{filename}/"
    response = s3_client.list_objects_v2(
        Bucket=BUCKET, Prefix=prefix
    )
    versions = []
    dates = []
    
    if 'Contents' not in response:
        return False

    for i, version in enumerate(response['Contents']):
        version_id = version['Key'].split('/')[-1].split('.')[0]
        version = {
            'version_id': version_id,
            'last_modified': version['LastModified'].strftime('%Y-%m-%d %H:%M:%S'),
            'storage_class': version['StorageClass'],
            'size': version['Size'],
            'is_latest': 'false'
        }
        dates.append([i, datetime.strptime(version_id, DATETIME_FORMAT)])
        versions.append(version)
    
    # Obtener el index de la fecha máxima
    latest_index = max(dates, key=lambda x: x[1])[0]
    # Modificar el parametro del archivo con la versión más reciente
    versions[latest_index]['is_latest'] = 'true'
    
    if max_index:
        return versions, latest_index
        
    return versions

def get_latest_version(contract_number: str, filename: str) -> str:
    """
    Get latest version of a file.
    """
    versions, max_index = get_versions_of_file(contract_number, filename, max_index=True)
    latest_version = versions[max_index]['version_id']
    
    return latest_version

def key_exists_in_bucket(s3_key: str) -> Union[Dict, bool]:
    """
    Checks if a key exists in a bucket.
    """
    s3_client = boto3.client('s3')
    try:
        resp = s3_client.head_object(Bucket=BUCKET, Key=s3_key)
    except ClientError as e:
        print(e.response['Error'])
        return False
    return resp

def get_filenames_in_contract_number(contract_number:str) -> Union[Dict, bool]:
    """
    Get filenames that are in a contract_number
    """
    s3 = boto3.client('s3')
    if not contract_number.endswith('/'):
        contract_number = contract_number + '/' 
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=contract_number, Delimiter='/')
    
    return resp.get('CommonPrefixes', False)
