import json
from stark.exceptions import ParseError
from stark.compat import dict_type
from stark.codecs.base import BaseCodec


class JSONCodec(BaseCodec):
    media_type = 'application/json'

    def decode(self, bytestring, **options):
        try:
            return json.loads(
                bytestring.decode('utf-8'),
                object_pairs_hook=dict_type
            )
        except ValueError as exc:
            raise ParseError(text='Malformed JSON. %s' % exc,
                             key='body',
                             code='codec') from None

    def encode(self, item, **options):
        return json.dumps(item, **options).encode('utf-8')
