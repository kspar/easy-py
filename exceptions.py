from requests import Response


class ErrorResponseException(Exception):
    def __init__(self, resp: Response, nested_exception: Exception = None):
        self.resp = resp
        self.nested_ex = nested_exception
        super().__init__(self.resp, nested_exception)


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
