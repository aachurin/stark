import json
from apistar.schemas.swagger import SWAGGER
from stark.codecs import DocumentBaseCodec


class SwaggerCodec(DocumentBaseCodec):

    media_type = 'application/swagger'

    def encode(self, document, **options):
        schema_defs = {}
        paths = self.get_paths(document, schema_defs=schema_defs)
        swagger = SWAGGER.validate({
            'swagger': '2.0',
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
            swagger['components'] = {'schemas': schema_defs}

        if not document.url:
            swagger.pop('servers')

        kwargs = {
            'ensure_ascii': False,
            'indent': 4,
            'separators': (',', ': ')
        }
        return json.dumps(swagger, **kwargs).encode('utf-8')

