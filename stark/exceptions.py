from typing import Union
from stark.schema import Message, ValidationError, ParseError


__all__ = ('ValidationError', 'Message', 'ParseError', 'NoReverseMatch', 'NoCodecAvailable', 'ConfigurationError',
           'HTTPException', 'Found', 'BadRequest', 'Forbidden', 'NotFound', 'MethodNotAllowed', 'NotAcceptable',
           'UnsupportedMediaType')


class NoReverseMatch(Exception):
    """
    Raised by a Router when `reverse_url` is passed an invalid handler name.
    """
    pass


class NoCodecAvailable(Exception):
    pass


class ConfigurationError(Exception):
    pass


# HTTP exceptions

class HTTPException(Exception):
    default_status_code: int = None
    default_detail: str = None

    def __init__(self,
                 detail: Union[str, dict] = None,
                 status_code: int = None) -> None:
        self.detail = self.default_detail if (detail is None) else detail
        self.status_code = self.default_status_code if (status_code is None) else status_code
        assert self.detail is not None, '"detail" is required.'
        assert self.status_code is not None, '"status_code" is required.'

    def get_headers(self):
        return {}


class Found(HTTPException):
    default_status_code = 302
    default_detail = 'Found'

    def __init__(self,
                 location: str,
                 detail: Union[str, dict] = None,
                 status_code: int = None) -> None:
        self.location = location
        super().__init__(detail, status_code)

    def get_headers(self):
        return {'Location': self.location}


class BadRequest(HTTPException):
    default_status_code = 400
    default_detail = 'Bad request'


class Forbidden(HTTPException):
    default_status_code = 403
    default_detail = 'Forbidden'


class NotFound(HTTPException):
    default_status_code = 404
    default_detail = 'Not found'


class MethodNotAllowed(HTTPException):
    default_status_code = 405
    default_detail = 'Method not allowed'


class NotAcceptable(HTTPException):
    default_status_code = 406
    default_detail = 'Could not satisfy the request Accept header'


class Conflict(HTTPException):
    default_status_code = 409
    default_detail = 'Conflict'


class UnsupportedMediaType(HTTPException):
    default_status_code = 415
    default_detail = 'Unsupported Content-Type header in request'
