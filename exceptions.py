from requests import Response


class ResponseCodeNot200Exception(Exception):
    def __init__(self, resp: Response):
        self.resp = resp
        super().__init__(self.resp)

    def __str__(self):
        return f'Expected HTTP response code "200", but got "{self.resp.status_code}" : {self.resp.content}'


class EmptyResponseException(Exception):
    def __init__(self, resp: Response, super_exception: Exception):
        self.resp = resp
        self.nested_exception = super_exception
        super().__init__(self.resp, self.nested_exception)

    def __str__(self):
        return f'Unexpected empty response. Nested exception: {self.nested_exception}'
