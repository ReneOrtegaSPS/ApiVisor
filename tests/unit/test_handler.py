import json, time
from typing import Tuple, Dict

import pytest
import requests

from conftest import DefaultTestValues

def get_statuscode_and_body_from_response(response: Dict) -> Tuple[int, Dict]:
    return_response = json.loads(response['Payload'].read().decode())
    
    return_response_status = return_response.get('statusCode')
    return_response_body = json.loads(return_response.get('body', '{}'))
    return return_response_status, return_response_body

@pytest.mark.common_errors
def test_no_body(request_no_body: Dict, lambda_client):
    """
    Test endpoints that require a body in the request. They should respond with an 400 error.
    """
    functions_with_body_required = [
        'CreateFunction', 'DeleteFunction', 'DismissFunction', 'GetFunction',
        'ListFunction', 'ListVersionsFunction', 'PresignedUrlFunction', 
        'UpdateFunction',
    ]

    for function_name in functions_with_body_required:
        response = lambda_client.invoke(FunctionName=function_name, 
            Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
        )
        status_code_resp, body_resp = get_statuscode_and_body_from_response(response)
        assert status_code_resp == 400
        assert body_resp == {'error': 'A body in the request is required.'}

@pytest.mark.common_errors
def test_no_header(request_no_header: Dict, lambda_client):
    """
    Test endpoints that require a header in the request. They should respond with an 400 error.
    """
    functions_with_header_required = [
        'CreateFunction', 'UpdateFunction',
    ]
    for function_name in functions_with_header_required:
        response = lambda_client.invoke(FunctionName=function_name, 
            Payload=bytes(json.dumps(request_no_header), encoding='utf-8')
        )
        status_code_resp, body_resp = get_statuscode_and_body_from_response(response)

        assert status_code_resp == 400
        assert body_resp == {'error': "Request Content Type Headers must be 'application/json' or 'multipart/form-data'"}

@pytest.mark.common_errors
def test_wrong_json_body(request_no_body: Dict, lambda_client):
    """
    Test endpoints that require a particular body format in the request.
    They should respond with an 400 error.
    """
    request_no_body['body'] = 'wrong body format'
    request_no_body['headers']['content-type'] = 'application/json'

    functions_with_header_required = [
        'CreateFunction', 'UpdateFunction',
    ]

    for function_name in functions_with_header_required:
        response = lambda_client.invoke(FunctionName=function_name, 
            Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
        )
    
    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)
    assert status_code_resp == 400
    assert body_resp.get('error', '').endswith('parameter(s) is/are missing.')

@pytest.mark.normal_flow
def test_create(request_no_body: Dict, lambda_client):
    """
    Test the /_create endpoint, it tries to create a new file.
    It should respond with an 201 code.
    """
    test_file = DefaultTestValues().load_test_versioned_file()

    test_file['filename'] = DefaultTestValues.filename
    test_file['contract_number'] = DefaultTestValues.contract_number

    request_no_body['headers']['content-type'] = 'application/json'
    request_no_body['body'] = json.dumps(test_file)

    response = lambda_client.invoke(FunctionName="CreateFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )
    
    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)
    assert status_code_resp == 201
    assert body_resp.get('message') == 'File created.'

@pytest.mark.normal_flow
def test_create_file_exist(request_no_body: Dict, lambda_client):
    """
    Test the /_create endpoint, it tries to create a file that already exists.
    It should throw a 400 error with a custom message indicating that.
    """
    test_file = DefaultTestValues().load_test_versioned_file()

    test_file['filename'] = DefaultTestValues.filename
    test_file['contract_number'] = DefaultTestValues.contract_number

    request_no_body['headers']['content-type'] = 'application/json'
    request_no_body['body'] = json.dumps(test_file)

    response = lambda_client.invoke(FunctionName="CreateFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )
    
    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)
    assert status_code_resp == 400
    assert body_resp.get('error') == 'A filename already exists in that contract_number.'

@pytest.mark.normal_flow
def test_update(request_no_body: Dict, lambda_client):
    """
    Test the /_update endpoint, it tries to update a file that already exists.
    It should respond with a 201 code.
    """
    test_file = DefaultTestValues().load_test_current_file()

    test_file['filename'] = DefaultTestValues.filename
    test_file['contract_number'] = DefaultTestValues.contract_number

    request_no_body['headers']['content-type'] = 'application/json'
    request_no_body['body'] = json.dumps(test_file)

    response = lambda_client.invoke(FunctionName="UpdateFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )
    
    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)
    assert status_code_resp == 201
    assert body_resp.get('message') == 'File updated.'

@pytest.mark.normal_flow
def test_list_files(request_no_body: Dict, lambda_client):
    """
    Test the /_list endpoint, it tries to list all the files inside a contract.
    It should respond with a 200 code and with only one item; the item must be the same
    that was previously created.
    """
    body = {
        'contract_number': DefaultTestValues.contract_number
    }

    request_no_body['headers']['content-type'] = 'application/json'
    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="ListFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )
    
    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)
    
    assert status_code_resp == 200
    assert len(body_resp['filename_items']) == 1
    
    file_info = body_resp['filename_items'][0]
    assert file_info['filename'] == DefaultTestValues.filename
    assert file_info['archived'] == False
    assert 'size' in file_info
    assert 'last_modified' in file_info

@pytest.mark.normal_flow
def test_list_versions(request_no_body: Dict, lambda_client):
    """
    Test the /_list_versions endpoint, it tries to list all the versions of a file.
    It should respond with a 200 code and with only two versions. It then saves the
    versions id to download the file in later tests.
    """

    body = {
        'contract_number': DefaultTestValues.contract_number,
        'filename': DefaultTestValues.filename
    }
    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="ListVersionsFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )

    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)

    assert status_code_resp == 200
    assert len(body_resp['versions']) == 2
    
    versions = body_resp['versions']
    version_data = {}
    for version in versions:
        assert 'version_id' in version
        assert 'last_modified' in version
        assert 'is_latest' in version
        assert 'size' in version
        assert version['archived'] == False

        if version['is_latest'] == True:
            version_data['current_file_version'] = version['version_id']
        elif version['is_latest'] == False:
            version_data['versioned_file_version'] = version['version_id']
    DefaultTestValues().save_data(version_data)

@pytest.mark.normal_flow
def test_get_file(request_no_body: Dict, lambda_client):
    """
    Test the /_get endpoint, it tries to get a file inside a contract.
    It should respond with a 200 code and with the latest file.
    """
    body = {
        'contract_number': DefaultTestValues.contract_number,
        'filename': DefaultTestValues.filename
    }
    # load the file which is expected to return
    expected_file = DefaultTestValues().load_test_current_file()
    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="GetFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )

    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)    

    assert status_code_resp == 200
    assert body_resp['filename'] == DefaultTestValues.filename
    assert body_resp['file'] == expected_file['file']
    assert body_resp['content_type'] == expected_file['content_type']

@pytest.mark.normal_flow
def test_get_current_file(request_no_body: Dict, lambda_client):
    """
    Test the /_get endpoint, it tries to get the current file version.
    It should respond with a 200 code and with the latest file.
    """
    test_data = DefaultTestValues().load_data()

    body = {
        'contract_number': DefaultTestValues.contract_number,
        'filename': DefaultTestValues.filename,
        'version_id': test_data['current_file_version']
    }
    # load the file which is expected to return
    expected_file = DefaultTestValues().load_test_current_file()
    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="GetFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )

    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)    

    assert status_code_resp == 200
    assert body_resp['filename'] == DefaultTestValues.filename
    assert body_resp['file'] == expected_file['file']
    assert body_resp['content_type'] == expected_file['content_type']

@pytest.mark.normal_flow
def test_get_versioned_file(request_no_body: Dict, lambda_client):
    """
    Test the /_get endpoint, it tries to get a version file.
    It should respond with a 200 code and with the corresponding 
    version.
    """
    test_data = DefaultTestValues().load_data()

    body = {
        'contract_number': DefaultTestValues.contract_number,
        'filename': DefaultTestValues.filename,
        'version_id': test_data['versioned_file_version']
    }
    request_no_body['body'] = json.dumps(body)

    # load the file which is expected to return
    expected_file = DefaultTestValues().load_test_versioned_file()

    response = lambda_client.invoke(FunctionName="GetFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )

    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)    

    assert status_code_resp == 200
    assert body_resp['filename'] == DefaultTestValues.filename
    assert body_resp['file'] == expected_file['file']
    assert body_resp['content_type'] == expected_file['content_type']

@pytest.mark.normal_flow
def test_dismiss_contract_number(request_no_body: Dict, lambda_client):
    """
    Test the /_dismiss endpoint, it tries to dismiss a contract.
    It should respond with a 200 code and with a custom message.
    """
    body = {
        'contract_number': DefaultTestValues.contract_number,
    }
    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="DismissFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )

    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)    

    assert status_code_resp == 200
    assert body_resp.get('message') == 'Files dismissed succesfully.'

@pytest.mark.normal_flow
def test_dismiss_already_dismissed_contract_number(request_no_body: Dict, lambda_client):
    """
    Test the /_dismiss endpoint, it tries to dismiss an already dismissed contract.
    It should respond with a 400 code and with a custom message.
    """
    body = {
        'contract_number': DefaultTestValues.contract_number,
    }
    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="DismissFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )

    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)    

    assert status_code_resp == 400
    assert body_resp.get('error') == 'Files have already been dismissed.'

@pytest.mark.normal_flow
def test_delete_files(request_no_body: Dict, lambda_client):
    """
    Test the /_delete endpoint, it tries to delete both versions of the file.
    It should respond both times with an 200 status code and a custom message.
    """
    test_data = DefaultTestValues().load_data()
    versions = [test_data[version] for version in ['versioned_file_version', 'current_file_version']]

    for version in versions:
        body = {
            'contract_number': DefaultTestValues.contract_number,
            'filename': DefaultTestValues.filename,
            'version_id': version
        }

        request_no_body['body'] = json.dumps(body)

        response = lambda_client.invoke(FunctionName="DeleteFunction", 
            Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
        )

        status_code_resp, body_resp = get_statuscode_and_body_from_response(response)    

        assert status_code_resp == 200
        assert body_resp.get('message') == 'File deleted.'

@pytest.mark.normal_flow
def test_delete_already_deleted_files(request_no_body: Dict, lambda_client):
    """
    Test the /_dismiss endpoint, it tries to delete a non-existent file.
    It should respond with a 404 code and with a custom message.
    """
    test_data = DefaultTestValues().load_data()
    versions = [test_data[version] for version in ['versioned_file_version', 'current_file_version']]

    for version in versions:
        body = {
            'contract_number': DefaultTestValues.contract_number,
            'filename': DefaultTestValues.filename,
            'version_id': version
        }

        request_no_body['body'] = json.dumps(body)

        response = lambda_client.invoke(FunctionName="DeleteFunction", 
            Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
        )

        status_code_resp, body_resp = get_statuscode_and_body_from_response(response)    

        assert status_code_resp == 404
        assert body_resp.get('error') == 'File not found.'

@pytest.mark.big_files_flow
def test_create_wrong_big_file(request_no_body: Dict, lambda_client):
    """
    Test the /_presigned_url endpoint, it tries to upload a wrong-formatted file.
    It should respond with a 204 code.
    """
    body = {
        'contract_number': DefaultTestValues.contract_number,
        'filename': DefaultTestValues.filename,
    }

    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="PresignedUrlFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )

    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)    

    assert status_code_resp == 200
    assert 'url' in body_resp

    presigned_url_fields = body_resp['fields']

    assert 'key' in presigned_url_fields
    assert 'AWSAccessKeyId' in presigned_url_fields
    # assert 'x-amz-security-token' in presigned_url_fields
    assert 'policy' in presigned_url_fields
    assert 'signature' in presigned_url_fields

    headers = {
        "Host": "visor-api-dev-temp-bucket.s3.amazonaws.com"
    }

    big_file = DefaultTestValues().load_test_big_file()
    del big_file['content_type']
    
    upload_response = requests.post(body_resp['url'], 
        data=presigned_url_fields, files={'file': json.dumps(big_file)}, headers=headers
    )
    assert upload_response.status_code == 204

@pytest.mark.big_files_flow
def test_check_no_wrong_file_in_bucket(request_no_body: Dict, lambda_client):
    """
    Test the /_list endpoint, it tries to get the wrong-formatted file.
    It should respond with a 404 code, since the file is not formatted properly.
    """
    time.sleep(30)
    body = {
        'contract_number': DefaultTestValues.contract_number,
        'filename': DefaultTestValues.filename,
    }

    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="ListFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )
    
    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)
    
    assert status_code_resp == 404
    assert body_resp.get('error') == 'Contract Number not found.'
    
@pytest.mark.big_files_flow
def test_create_big_file(request_no_body: Dict, lambda_client):
    """
    Test the /_presigned_url endpoint, it tries to upload a file.
    It should respond with a 204 code.
    """
    body = {
        'contract_number': DefaultTestValues.contract_number,
        'filename': DefaultTestValues.filename,
    }

    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="PresignedUrlFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )

    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)    

    assert status_code_resp == 200
    assert 'url' in body_resp

    presigned_url_fields = body_resp['fields']

    assert 'key' in presigned_url_fields
    assert 'AWSAccessKeyId' in presigned_url_fields
    # assert 'x-amz-security-token' in presigned_url_fields
    assert 'policy' in presigned_url_fields
    assert 'signature' in presigned_url_fields

    headers = {
        "Host": "visor-api-dev-temp-bucket.s3.amazonaws.com"
    }

    big_file = DefaultTestValues().load_test_big_file()
    
    upload_response = requests.post(body_resp['url'], 
        data=presigned_url_fields, files={'file': json.dumps(big_file)}, headers=headers
    )
    
    assert upload_response.status_code == 204

@pytest.mark.big_files_flow
def test_check_file_in_bucket(request_no_body: Dict, lambda_client):
    """
    Test the /_list endpoint, it tries to get the wrong-formatted file.
    It should respond with a 200 code, with only one version.
    """
    time.sleep(30)
    body = {
        'contract_number': DefaultTestValues.contract_number,
        'filename': DefaultTestValues.filename
    }
    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="ListVersionsFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )

    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)

    assert status_code_resp == 200
    assert len(body_resp['versions']) == 1
    
    version = body_resp['versions'][0]
    version_data = {}
    assert 'version_id' in version
    assert 'last_modified' in version
    assert 'is_latest' in version
    assert 'size' in version
    assert version['archived'] == False

    version_data = {'big_file_version': version['version_id']}
    DefaultTestValues().save_data(version_data)

@pytest.mark.big_files_flow
def test_get_current_big_file(request_no_body: Dict, lambda_client):
    """
    Test the /_get endpoint, it tries to get the big file.
    It should respond with a 200 code and with the presigned url.
    """
    big_file_version = DefaultTestValues().load_data()['big_file_version']

    body = {
        'contract_number': DefaultTestValues.contract_number,
        'filename': DefaultTestValues.filename,
    }
    # load the file which is expected to return
    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="GetFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )

    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)
    assert status_code_resp == 200
    assert 'presigned_url' in body_resp

    presigned_url = body_resp['presigned_url']
    contract_number, filename, version = presigned_url.split('/', 3)[-1].split('/')
    assert contract_number == DefaultTestValues.contract_number
    assert filename == DefaultTestValues.filename
    assert version.startswith(big_file_version)

@pytest.mark.big_files_flow
def test_delete_big_file(request_no_body: Dict, lambda_client):
    """
    Test the /_delete endpoint, it tries to delete the big file.
    It should respond a 200 status code and a custom message.
    """
    version = DefaultTestValues().load_data()['big_file_version']
    
    body = {
        'contract_number': DefaultTestValues.contract_number,
        'filename': DefaultTestValues.filename,
        'version_id': version
    }

    request_no_body['body'] = json.dumps(body)

    response = lambda_client.invoke(FunctionName="DeleteFunction", 
        Payload=bytes(json.dumps(request_no_body), encoding='utf-8')
    )

    status_code_resp, body_resp = get_statuscode_and_body_from_response(response)    

    assert status_code_resp == 200
    assert body_resp.get('message') == 'File deleted.'