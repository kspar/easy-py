import json
from typing import Callable, Dict, Type, Tuple

import requests

from exceptions import ErrorResponseException, ResponseMissingKeyException, ErrorResp
from ez import Resp


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


def handle_response(code_to_instance: Dict[int, Tuple[requests.Response, Type[Callable]]]) -> Dict[int, Resp]:
    out = dict()
    for expected_code, (resp, instance) in code_to_instance.items():
        assert isinstance(expected_code, int)
        assert isinstance(resp, requests.Response)
        assert isinstance(instance, Callable)

        try:
            j: dict = resp.json()
        except json.decoder.JSONDecodeError as e:
            raise ErrorResponseException(resp, None, e)

        try:
            if expected_code == resp.status_code:
                dto: Resp = instance(resp.status_code, resp, **j)
                out[expected_code] = dto

            else:
                error_rsp: ErrorResp = ErrorResp(**j)
                raise ErrorResponseException(resp, error_rsp)

        except KeyError as e:
            raise ResponseMissingKeyException(resp, e)

    return out
