from dataclasses import dataclass
from typing import Dict

from requests import Response


@dataclass
class ErrorResp:
    id: str
    code: str
    attrs: Dict[str, str]
    log_msg: str


class ErrorResponseException(Exception):
    def __init__(self, resp: Response, error_resp: ErrorResp = None, nested_exception: Exception = None):
        self.resp = resp
        self.error_resp = error_resp
        self.nested_ex = nested_exception
        super().__init__(self.resp, error_resp, nested_exception)


class EmptyResponseException(Exception):
    def __init__(self, resp: Response, nested_exception: Exception = None):
        self.resp = resp
        self.nested_exception = nested_exception
        super().__init__(self.resp, self.nested_exception)


class ResponseMissingKeyException(Exception):
    def __init__(self, resp: Response, nested_exception: Exception = None):
        self.resp = resp
        self.nested_exception = nested_exception
        super().__init__(self.resp, self.nested_exception)
