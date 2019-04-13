import json
from stark import schemas, exceptions
from stark.codecs.base import BaseCodec
from stark.compat import dict_type


class JSONSchemaCodec(BaseCodec):
    media_type = 'application/schema+json'
    format = 'jsonschema'

    def decode(self, bytestring, **options):
        try:
            data = json.loads(
                bytestring.decode('utf-8'),
                object_pairs_hook=dict_type
            )
        except ValueError as exc:
            raise exceptions.ParseError(text='Malformed JSON. %s' % exc,
                                        key='body',
                                        code='codec') from None
        return schemas.from_json_schema(data)

    def encode(self, item, **options):
        defs = schemas.SchemaDefinitions()
        struct = schemas.to_json_schema(item, defs)
        if defs:
            struct['definitions'] = defs
        indent = options.get('indent')
        if indent:
            kwargs = {
                'ensure_ascii': False,
                'indent': 4,
                'separators': (',', ': ')
            }
        else:
            kwargs = {
                'ensure_ascii': False,
                'indent': None,
                'separators': (',', ':')
            }
        return json.dumps(struct, **kwargs).encode('utf-8')
