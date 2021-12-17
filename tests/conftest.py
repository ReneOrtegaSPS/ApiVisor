import json, os
from typing import Dict, Type

import pytest
import boto3
import botocore


class DefaultTestValues:
    contract_number = 'UnitTesting'
    filename = 'FileTest'

    def load_data(self) -> Dict:
        filepath = 'unit/tests_storage/data.json' 
        if os.stat(filepath).st_size == 0:
            return {}

        with open(filepath, 'r') as f:
            data = json.load(f)

        return data

    def save_data(self, data: Dict):
        current_data = self.load_data()
        current_data.update(data)
        print(data)
        print(current_data)

        with open('unit/tests_storage/data.json', 'w') as f:
            json.dump(current_data, f)

    def load_test_current_file(self) -> Dict:
        with open('unit/dummy_files/current_file.json', 'r') as f:
            test_file = json.load(f)
        return test_file

    def load_test_versioned_file(self) -> Dict:
        with open('unit/dummy_files/versioned_file.json', 'r') as f:
            test_file = json.load(f)
        return test_file

    def load_test_big_file(self) -> Dict:
        with open('unit/dummy_files/big_file.json', 'r') as f:
            test_file = json.load(f)
        return test_file
        

def sample_request() -> Dict:
    """ Generates API GW Event"""

    return {
        "resource": "/{proxy+}",
        "path": "/path/to/resource",
        "httpMethod": "POST",
        "isBase64Encoded": "false",
        "pathParameters": {
            "proxy": "/path/to/resource"
        },
        "stageVariables": {
            "baz": "qux"
        },
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, sdch",
            "Accept-Language": "en-US,en;q=0.8",
            "Cache-Control": "max-age=0",
            "CloudFront-Forwarded-Proto": "https",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-Mobile-Viewer": "false",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Tablet-Viewer": "false",
            "CloudFront-Viewer-Country": "US",
            "Host": "1234567890.execute-api.us-east-1.amazonaws.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Custom User Agent String",
            "Via": "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)",
            "X-Amz-Cf-Id": "cDehVQoZnx43VYQb9j2-nvCh-9z396Uhbp027Y2JvkCPNLmGJHqlaA==",
            "X-Forwarded-For": "127.0.0.1, 127.0.0.2",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https"
        },
        "requestContext": {
            "accountId": "123456789012",
            "resourceId": "123456",
            "stage": "prod",
            "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {
            "cognitoIdentityPoolId": "null",
            "accountId": "null",
            "cognitoIdentityId": "null",
            "caller": "null",
            "accessKey": "null",
            "sourceIp": "127.0.0.1",
            "cognitoAuthenticationType": "null",
            "cognitoAuthenticationProvider": "null",
            "userArn": "null",
            "userAgent": "Custom User Agent String",
            "user": "null"
            },
            "path": "/prod/path/to/resource",
            "resourcePath": "/{proxy+}",
            "httpMethod": "POST",
            "apiId": "1234567890",
            "protocol": "HTTP/1.1"
        }
    }

@pytest.fixture
def request_no_header() -> Dict:
    request = sample_request()
    request['body'] = 'some body'
    return request

@pytest.fixture
def request_no_body() -> Dict:
    return sample_request()

@pytest.fixture
def lambda_client():
    return boto3.client('lambda',
        region_name="us-west-2",
        endpoint_url="http://127.0.0.1:3001",
        use_ssl=False,
        verify=False,
        config=botocore.client.Config(
            signature_version=botocore.UNSIGNED,
            retries={'max_attempts': 0},
        )
    )