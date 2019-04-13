from stark.codecs.base import BaseCodec


class TextCodec(BaseCodec):

    media_type = 'text/*'

    def decode(self, bytestring, **options):
        return bytestring.decode('utf-8')

    def encode(self, item, **options):
        return item.encode('utf-8')
