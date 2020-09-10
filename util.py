import dataclasses
import json
import time
from typing import Callable, Dict, Type, Tuple

import requests

import auth
import conf
import data
from data import Resp
from exceptions import ErrorResponseException, ResponseMissingKeyException, ErrorResp, UnexpectedResponseException


def get_token_header(read_token: Callable[[data.Token], Tuple[str, int]],
                     save_tokens: Callable[[str, int, str], None]) -> Dict[str, str]:
    access_token_file, expires_at = read_token(data.Token.ACCESS)

    if access_token_file is None or time.time() > expires_at + conf.AUTH_TOKEN_MIN_VALID_SEC:
        auth.auth(read_token, save_tokens)
        access_token_file, expires_at = read_token(data.Token.ACCESS)

        if access_token_file is None or time.time() > expires_at + conf.AUTH_TOKEN_MIN_VALID_SEC:
            raise RuntimeError("Could not get/refresh tokens")

    return {"Authorization": f"Bearer {access_token_file[data.Token.ACCESS.value]}"}


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


def simple_get_request(path: str, instance: Callable, read_token: Callable[[data.Token], Tuple[str, int]],
                       save_tokens: Callable[[str, int, str], None]):
    resp: requests.Response = requests.get(path, headers=get_token_header(read_token, save_tokens))
    dto = handle_response(resp, {200: instance})
    assert isinstance(dto, instance)
    return dto


def post_request(path: str, req_object: dataclasses, read_token: Callable[[data.Token], Tuple[str, int]],
                 save_tokens: Callable[[str, int, str], None]) -> int:
    data = json.dumps(dataclasses.asdict(req_object)).encode("utf-8")
    resp: requests.Response = requests.post(path, data=data, headers=get_token_header(read_token, save_tokens))
    return resp.status_code
