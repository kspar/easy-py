import dataclasses
import json
import os
import time
from typing import Callable, Dict, Type

import requests

import auth
import conf
from data import Resp
from exceptions import ErrorResponseException, ResponseMissingKeyException, ErrorResp, UnexpectedResponseException


def get_token_header() -> Dict[str, str]:
    access_token_file, expires_at = None, 0

    if os.path.isfile("access_token"):
        access_token_file = json.loads(get_file_content("access_token").strip())
        expires_at = access_token_file["expires_at"]

    if access_token_file is None or time.time() > expires_at + conf.AUTH_TOKEN_MIN_VALID_SEC:
        auth.auth()

        if os.path.isfile("access_token"):
            access_token_file = json.loads(get_file_content("access_token").strip())
            expires_at = access_token_file["expires_at"]

        if access_token_file is None or time.time() > expires_at + conf.AUTH_TOKEN_MIN_VALID_SEC:
            raise RuntimeError("Could not get/refresh tokens")

    return {"Authorization": f"Bearer {access_token_file['access_token']}"}


def get_file_content(file_name) -> str:
    with open(file_name, encoding="utf-8") as f:
        return f.read()


def write_restricted_file(file_name, file_content):
    with open(os.open(file_name, os.O_CREAT | os.O_WRONLY, 0o600), "w") as f:
        f.write(file_content)


def contains_none(args) -> bool:
    return None in args


def assert_not_none(*args):
    if contains_none(args):
        raise ValueError("None arguments are not allowed in this function call.")


def handle_response(resp: requests.Response, code_to_instance: Dict[int, Type[Callable]]) -> Resp:
    try:
        j: dict = resp.json()
    except json.decoder.JSONDecodeError as e:
        raise ErrorResponseException(resp, None, e)

    try:
        if resp.status_code in code_to_instance:
            instance = code_to_instance[resp.status_code]
            dto: Resp = instance(resp.status_code, resp, **j)
            return dto

        else:
            error_rsp: ErrorResp = ErrorResp(**j)
            raise UnexpectedResponseException(resp, error_rsp)

    except KeyError as e:
        raise ResponseMissingKeyException(resp, e)


def simple_get_request(path: str, instance: Callable, header_func: Callable):
    resp: requests.Response = requests.get(path, headers=header_func())
    dto = handle_response(resp, {200: instance})
    assert isinstance(dto, instance)
    return dto


def post_request(path: str, req_object: dataclasses, header_func: Callable) -> int:
    data = json.dumps(dataclasses.asdict(req_object)).encode("utf-8")
    resp: requests.Response = requests.post(path, data=data, headers=header_func())
    return resp.status_code


def get_student_testing_header() -> Dict[str, str]:
    return {"Content-Type": "application/json",
            "oidc_claim_easy_role": "student",
            "oidc_claim_email": "foo@bar.com",
            "oidc_claim_given_name": "Foo",
            "oidc_claim_family_name": "Bar",
            "oidc_claim_preferred_username": "fp"}


def get_teacher_testing_header() -> Dict[str, str]:
    return {"Content-Type": "application/json",
            "oidc_claim_easy_role": "teacher",
            "oidc_claim_email": "foo@bar.com",
            "oidc_claim_given_name": "Foo",
            "oidc_claim_family_name": "Bar",
            "oidc_claim_preferred_username": "fp"}
