from urllib.parse import urljoin

from stark import validators
from stark.codecs import OpenAPICodec
from stark.codecs.jsonschema import JSON_SCHEMA
from stark.document import Document, Link


SCHEMA_REF = validators.Object(
    properties={'$ref': validators.String(pattern='^#/components/schemas/')}
)
RESPONSE_REF = validators.Object(
    properties={'$ref': validators.String(pattern='^#/components/responses/')}
)
SWAGGER = validators.Object(
    def_name='Swagger',
    title='Swagger',
    properties=[
        ('swagger', validators.String()),
        ('info', validators.Ref('Info')),
        ('paths', validators.Ref('Paths')),
        ('host', validators.String()),
        ('basePath', validators.String()),
        ('schemes', validators.Array(items=validators.String())),
        ('consumes', validators.Array(items=validators.String())),
        ('produces', validators.Array(items=validators.String())),
        ('definitions', validators.Object(additional_properties=validators.Any())),
        ('parameters', validators.Object(additional_properties=validators.Ref('Parameters'))),
        ('responses', validators.Object(additional_properties=validators.Ref('Responses'))),
        ('securityDefinitions', validators.Object(additional_properties=validators.Ref('SecurityScheme'))),
        ('security', validators.Array(items=validators.Ref('SecurityRequirement'))),
        ('tags', validators.Array(items=validators.Ref('Tag'))),
        ('externalDocs', validators.Ref('ExternalDocumentation')),
    ],
    pattern_properties={
        '^x-': validators.Any(),
    },
    additional_properties=False,
    required=['swagger', 'info', 'paths'],
    definitions={
        'Info': validators.Object(
            properties=[
                ('title', validators.String()),
                ('description', validators.String(format='textarea')),
                ('termsOfService', validators.String(format='url')),
                ('contact', validators.Ref('Contact')),
                ('license', validators.Ref('License')),
                ('version', validators.String()),
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
            required=['title', 'version']
        ),
        'Contact': validators.Object(
            properties=[
                ('name', validators.String()),
                ('url', validators.String(format='url')),
                ('email', validators.String(format='email')),
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
        ),
        'License': validators.Object(
            properties=[
                ('name', validators.String()),
                ('url', validators.String(format='url')),
            ],
            required=['name'],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
        ),
        'Paths': validators.Object(
            pattern_properties=[
                ('^/', validators.Ref('Path')),
                ('^x-', validators.Any()),
            ],
            additional_properties=False,
        ),
        'Path': validators.Object(
            properties=[
                ('summary', validators.String()),
                ('description', validators.String(format='textarea')),
                ('get', validators.Ref('Operation')),
                ('put', validators.Ref('Operation')),
                ('post', validators.Ref('Operation')),
                ('delete', validators.Ref('Operation')),
                ('options', validators.Ref('Operation')),
                ('head', validators.Ref('Operation')),
                ('patch', validators.Ref('Operation')),
                ('trace', validators.Ref('Operation')),
                ('parameters', validators.Array(items=validators.Ref('Parameter'))),  # TODO: | ReferenceObject
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
        ),
        'Operation': validators.Object(
            properties=[
                ('tags', validators.Array(items=validators.String())),
                ('summary', validators.String()),
                ('description', validators.String(format='textarea')),
                ('externalDocs', validators.Ref('ExternalDocumentation')),
                ('operationId', validators.String()),
                ('consumes', validators.Array(items=validators.String())),
                ('produces', validators.Array(items=validators.String())),
                ('parameters', validators.Array(items=validators.Ref('Parameter'))),  # TODO: | ReferenceObject
                ('responses', validators.Ref('Responses')),
                ('schemes', validators.Array(items=validators.String())),
                ('deprecated', validators.Boolean()),
                ('security', validators.Array(validators.Ref('SecurityRequirement'))),
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
        ),
        'ExternalDocumentation': validators.Object(
            properties=[
                ('description', validators.String(format='textarea')),
                ('url', validators.String(format='url')),
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
            required=['url']
        ),
        'Parameter': validators.Object(
            properties=[
                ('name', validators.String()),
                ('in', validators.String(enum=['body', 'query', 'header', 'path', 'cookie'])),
                ('description', validators.String(format='textarea')),
                ('required', validators.Boolean()),
                ('deprecated', validators.Boolean()),
                ('allowEmptyValue', validators.Boolean()),
                ('style', validators.String()),
                ('schema', JSON_SCHEMA | SCHEMA_REF),
                ('type', validators.String()),
                ('format', validators.String()),
                ('allowEmptyValue', validators.Boolean()),
                # TODO: Other fields
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
            required=['name', 'in']
        ),
        'RequestBody': validators.Object(
            properties=[
                ('description', validators.String()),
                ('content', validators.Object(additional_properties=validators.Ref('MediaType'))),
                ('required', validators.Boolean()),
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
        ),
        'Responses': validators.Object(
            properties=[
                ('default', validators.Ref('Response') | RESPONSE_REF),
            ],
            pattern_properties=[
                ('^([1-5][0-9][0-9]|[1-5]XX)$', validators.Ref('Response') | RESPONSE_REF),
                ('^x-', validators.Any()),
            ],
            additional_properties=False,
        ),
        'Response': validators.Object(
            properties=[
                ('description', validators.String()),
                ('content', validators.Object(additional_properties=validators.Ref('MediaType'))),
                ('headers', validators.Object(additional_properties=validators.Ref('Header'))),
                # TODO: Header | ReferenceObject
                # TODO: links
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
        ),
        'MediaType': validators.Object(
            properties=[
                ('schema', JSON_SCHEMA | SCHEMA_REF),
                ('example', validators.Any()),
                # TODO 'examples', 'encoding'
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
        ),
        'Header': validators.Object(
            properties=[
                ('description', validators.String(format='textarea')),
                ('required', validators.Boolean()),
                ('deprecated', validators.Boolean()),
                ('allowEmptyValue', validators.Boolean()),
                ('style', validators.String()),
                ('schema', JSON_SCHEMA | SCHEMA_REF),
                ('example', validators.Any()),
                # TODO: Other fields
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False
        ),
        'Components': validators.Object(
            properties=[
                ('schemas', validators.Object(additional_properties=JSON_SCHEMA)),
                ('responses', validators.Object(additional_properties=validators.Ref('Response'))),
                ('parameters', validators.Object(additional_properties=validators.Ref('Parameter'))),
                ('securitySchemes', validators.Object(additional_properties=validators.Ref('SecurityScheme'))),
                # TODO: Other fields
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
        ),
        'Tag': validators.Object(
            properties=[
                ('name', validators.String()),
                ('description', validators.String(format='textarea')),
                ('externalDocs', validators.Ref('ExternalDocumentation')),
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
            required=['name']
        ),
        'SecurityRequirement': validators.Object(
            additional_properties=validators.Array(items=validators.String()),
        ),
        'SecurityScheme': validators.Object(
            properties=[
                ('type', validators.String(enum=['basic', 'apiKey', 'oauth2'])),
                ('description', validators.String(format='textarea')),
                ('name', validators.String()),
                ('in', validators.String(enum=['query', 'header', 'cookie'])),
                ('scheme', validators.String()),
                ('bearerFormat', validators.String()),
                ('flows', validators.Any()),  # TODO: OAuthFlows
                ('openIdConnectUrl', validators.String()),
            ],
            pattern_properties={
                '^x-': validators.Any(),
            },
            additional_properties=False,
            required=['type']
        ),
    }
)


METHODS = [
    'get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace'
]


class SwaggerCodec(OpenAPICodec):
    media_type = 'application/swagger'
    format = 'swagger'

    def validate_document(self, document, schema_defs, paths):
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

        return swagger

    def validate_data(self, data):
        data = SWAGGER.validate(data)

        title = self.lookup(data, ['info', 'title'])
        description = self.lookup(data, ['info', 'description'])
        version = self.lookup(data, ['info', 'version'])
        host = self.lookup(data, ['host'])
        path = self.lookup(data, ['basePath'], '/')
        scheme = self.lookup(data, ['schemes', 0], 'https')
        base_url = None
        if host:
            base_url = '%s://%s%s' % (scheme, host, path)
        schema_definitions = self.get_schema_definitions(data)
        content = self.get_content(data, base_url, schema_definitions)
        return Document(title=title, description=description, version=version, url=base_url, content=content)

    def get_link(self, base_url, path, path_info, operation, operation_info, schema_definitions):
        """
        Return a single link in the document.
        """
        name = operation_info.get('operationId')
        title = operation_info.get('summary')
        description = operation_info.get('description')

        if name is None:
            name = self.simple_slugify(title)
            if not name:
                return None

        # Allow path info and operation info to override the base url.
        base_url = self.lookup(path_info, ['servers', 0, 'url'], default=base_url)
        base_url = self.lookup(operation_info, ['servers', 0, 'url'], default=base_url)

        # Parameters are taken both from the path info, and from the operation.
        parameters = path_info.get('parameters', [])
        parameters += operation_info.get('parameters', [])

        fields = [
            self.get_field(parameter, schema_definitions)
            for parameter in parameters
        ]

        default_encoding = None
        if any([field.location == 'body' for field in fields]):
            default_encoding = 'application/json'
        encoding = self.lookup(operation_info, ['consumes', 0], default_encoding)

        return Link(
            name=name,
            url=urljoin(base_url, path),
            method=operation,
            title=title,
            description=description,
            fields=fields,
            encoding=encoding
        )
