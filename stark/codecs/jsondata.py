import json
import collections

from stark.codecs.base import BaseCodec
from stark.exceptions import ParseError, ErrorMessage


class JSONCodec(BaseCodec):

    media_type = 'application/json'

    def decode(self, bytestring, **options):
        try:
            return json.loads(
                bytestring.decode('utf-8'),
                object_pairs_hook=collections.OrderedDict
            )
        except ValueError as exc:
            message = ErrorMessage(text='Malformed JSON. %s' % exc,
                                   index=['body'],
                                   code='parse_failed')
            raise ParseError(messages=[message]) from None

    def encode(self, item, **options):
        return json.dumps(item, **options).encode('utf-8')
