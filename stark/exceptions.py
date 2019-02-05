from typing import Union
from collections import namedtuple


Position = namedtuple('Position', ['line_no', 'column_no', 'index'])


class ErrorMessage:

    def __init__(self, text, code, index=None, position=None):
        self.text = text
        self.code = code
        self.index = index
        self.position = position

    def __eq__(self, other):
        return (
            self.text == other.text and
            self.code == other.code and
            self.index == other.index and
            self.position == other.position
        )

    def __repr__(self):
        return "%s(%s, code=%s, index=%s, position=%s)" % (
            self.__class__.__name__,
            repr(self.text),
            repr(self.code),
            repr(self.index),
            repr(self.position)
        )


class DecodeError(Exception):

    def __init__(self, messages, summary=None):
        self.messages = messages
        self.summary = summary
        super().__init__(messages)


class ValidationError(DecodeError):
    def as_dict(self):
        ret = {}
        for message in self.messages:
            lookup = ret
            if message.index:
                for key in message.index[:-1]:
                    lookup.setdefault(key, {})
                    lookup = lookup[key]
            key = message.index[-1] if message.index else None
            lookup[key] = message.text
        return ret


class ParseError(ValidationError):
    pass


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
    default_status_code = None  # type: int
    default_detail = None  # type: str

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


class UnsupportedMediaType(HTTPException):
    default_status_code = 415
    default_detail = 'Unsupported Content-Type header in request'
