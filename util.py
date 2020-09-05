import json
from typing import Callable, Dict, Type

import requests

from data import Resp
from exceptions import ErrorResponseException, ResponseMissingKeyException, ErrorResp, UnexpectedResponseException


def contains_none(args):
    return None in args


def assert_not_none(*args):
    if contains_none(args):
        raise ValueError("None arguments are not allowed in this function call.")


def get_student_testing_header():
    return {"Content-Type": "application/json",
            "oidc_claim_easy_role": "student",
            "oidc_claim_email": "foo@bar.com",
            "oidc_claim_given_name": "Foo",
            "oidc_claim_family_name": "Bar",
            "oidc_claim_preferred_username": "fp"}


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


def create_simple_get_request(path: str, instance: Callable):
    resp: requests.Response = requests.get(path, headers=get_student_testing_header())
    dto = handle_response(resp, {200: instance})
    assert isinstance(dto, instance)
    return dto
