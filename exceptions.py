import typing as T
from dataclasses import dataclass

from requests import Response


@dataclass
class ErrorResp:
    id: str
    code: str
    attrs: T.Dict[str, str]
    log_msg: str


class ErrorResponseException(Exception):
    def __init__(self, resp: Response, error_resp: ErrorResp = None, nested_exception: Exception = None):
        self.resp = resp
        self.error_resp = error_resp
        self.nested_ex = nested_exception
        # TODO: is this necessary?
        super().__init__(self.resp, error_resp, nested_exception)
