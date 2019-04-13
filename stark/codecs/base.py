from stark.exceptions import NoCodecAvailable


class BaseCodec:
    media_type = None

    def decode(self, bytestring, **options):
        raise NoCodecAvailable()

    def encode(self, item, **options):
        raise NoCodecAvailable()
