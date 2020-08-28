import json
from typing import Type, Callable

import requests

from exceptions import ErrorResponseException, ResponseMissingKeyException
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


def handle_response(resp: requests.Response, instance: Type[Callable]) -> Resp:
    resp_code: int = resp.status_code

    if resp_code == 200:
        try:
            j: dict = resp.json()

            dto: Resp = instance(resp_code, resp, **j)
        except json.decoder.JSONDecodeError as e:
            raise ErrorResponseException(resp, e)
        except KeyError as e:
            raise ResponseMissingKeyException(resp, e)
        return dto
    else:
        raise ErrorResponseException(resp)
