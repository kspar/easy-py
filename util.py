import json
from typing import Callable, Dict, Type

import requests

from data import Resp
from exceptions import ErrorResponseException, ResponseMissingKeyException, ErrorResp, UnexpectedResponseException


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
