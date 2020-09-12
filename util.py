import json
import typing as T

import requests

from data import Resp
from exceptions import ErrorResponseException, ErrorResp


def contains_none(args) -> bool:
    return None in args


def assert_not_none(*args):
    if contains_none(args):
        raise ValueError("None arguments are not allowed in this function call.")


def handle_response(resp: requests.Response, code_to_dto_class: T.Dict[int, T.Type[T.Any]]) -> Resp:
    if resp.text.strip() == '':
        # Empty response is treated like an empty JSON object
        json_response = {}
    else:
        try:
            json_response: dict = resp.json()
        except json.decoder.JSONDecodeError as e:
            # Not valid JSON
            raise ErrorResponseException(resp, None, e)

    if resp.status_code in code_to_dto_class:
        response_dto_class = code_to_dto_class[resp.status_code]
        return response_dto_class(resp.status_code, resp, **json_response)

    else:
        try:
            error_rsp = ErrorResp(**json_response)
            nested_exception = None
        except Exception as e:
            error_rsp = None
            nested_exception = e

        raise ErrorResponseException(resp, error_rsp, nested_exception)
