import json
from apistar.schemas.openapi import OPEN_API
from stark.codecs import DocumentBaseCodec


class OpenAPICodec(DocumentBaseCodec):

    media_type = 'application/vnd.oai.openapi'

    def encode(self, document, **options):
        schema_defs = {}
        paths = self.get_paths(document, schema_defs=schema_defs)
        openapi = OPEN_API.validate({
            'openapi': '3.0.0',
            'info': {
                'version': document.version,
                'title': document.title,
                'description': document.description
            },
            'servers': [{
                'url': document.url
            }],
            'paths': paths
        })

        if schema_defs:
            openapi['components'] = {'schemas': schema_defs}

        if not document.url:
            openapi.pop('servers')

        kwargs = {
            'ensure_ascii': False,
            'indent': 4,
            'separators': (',', ': ')
        }
        return json.dumps(openapi, **kwargs).encode('utf-8')
