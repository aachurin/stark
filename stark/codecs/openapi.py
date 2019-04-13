import re
import json
from urllib.parse import urljoin, urlparse
from stark import exceptions
from stark.codecs import BaseCodec
from stark.schemas import JSONSchema, to_json_schema, from_json_schema, SchemaDefinitions, Definitions
from stark.schemas import String, Choice, Object, Any, Reference, Array, Boolean
from stark.compat import dict_type
from stark.document import Document, Field, Link, Section


SchemaRef = Object(
    properties={'$ref': String(pattern='^#/components/schemas/')}
)

RequestBodyRef = Object(
    properties={'$ref': String(pattern='^#/components/requestBodies/')}
)

ResponseRef = Object(
    properties={'$ref': String(pattern='^#/components/responses/')}
)

definitions = SchemaDefinitions()

OpenAPI = Object(
    title='OpenAPI',
    properties={
        'openapi': String(),
        'info': Reference('Info', definitions=definitions),
        'servers': Array(items=Reference('Server', definitions=definitions)),
        'paths': Reference('Paths', definitions=definitions),
        'components': Reference('Components', definitions=definitions),
        'security': Array(items=Reference('SecurityRequirement', definitions=definitions)),
        'tags': Array(items=Reference('Tag', definitions=definitions)),
        'externalDocs': Reference('ExternalDocumentation', definitions=definitions),
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
    required=['openapi', 'info', 'paths']
)

definitions['JSONSchema'] = JSONSchema

definitions['Info'] = Object(
    properties={
        'title': String(allow_blank=True),
        'description': String(format='textarea', allow_blank=True),
        'termsOfService': String(format='url', allow_blank=True),
        'contact': Reference('Contact', definitions=definitions),
        'license': Reference('License', definitions=definitions),
        'version': String(allow_blank=True),
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
    required=['title', 'version']
)

definitions['Contact'] = Object(
    properties={
        'name': String(),
        'url': String(format='url'),
        'email': String(format='email'),
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
)

definitions['License'] = Object(
    properties={
        'name': String(),
        'url': String(format='url'),
    },
    required=['name'],
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
)

definitions['Server'] = Object(
    properties={
        'url': String(allow_blank=True),
        'description': String(format='textarea'),
        'variables': Object(additional_properties=Reference('ServerVariable', definitions=definitions)),
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
    required=['url']
)

definitions['ServerVariable'] = Object(
    properties={
        'enum': Array(items=String()),
        'default': String(),
        'description': String(format='textarea'),
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
    required=['default']
)

definitions['Paths'] = Object(
    pattern_properties={
        '^/': Reference('Path', definitions=definitions),
        '^x-': Any(),
    },
    additional_properties=False,
)

definitions['Path'] = Object(
    properties={
        'summary': String(),
        'description': String(format='textarea'),
        'get': Reference('Operation', definitions=definitions),
        'put': Reference('Operation', definitions=definitions),
        'post': Reference('Operation', definitions=definitions),
        'delete': Reference('Operation', definitions=definitions),
        'options': Reference('Operation', definitions=definitions),
        'head': Reference('Operation', definitions=definitions),
        'patch': Reference('Operation', definitions=definitions),
        'trace': Reference('Operation', definitions=definitions),
        'servers': Array(items=Reference('Server', definitions=definitions)),
        'parameters': Array(items=Reference('Parameter', definitions=definitions))  # TODO: | ReferenceObject
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
)

definitions['Operation'] = Object(
    properties={
        'tags': Array(items=String()),
        'summary': String(),
        'description': String(format='textarea'),
        'externalDocs': Reference('ExternalDocumentation', definitions=definitions),
        'operationId': String(),
        'parameters': Array(items=Reference('Parameter', definitions=definitions)),
        # TODO: | ReferenceObject
        'requestBody': RequestBodyRef | Reference('RequestBody', definitions=definitions),
        # TODO: RequestBody | ReferenceObject
        'responses': Reference('Responses', definitions=definitions),
        # TODO: 'callbacks'
        'deprecated': Boolean(),
        'security': Array(Reference('SecurityRequirement', definitions=definitions)),
        'servers': Array(items=Reference('Server', definitions=definitions)),
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
)

definitions['ExternalDocumentation'] = Object(
    properties={
        'description': String(format='textarea'),
        'url': String(format='url'),
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
    required=['url']
)

definitions['Parameter'] = Object(
    properties={
        'name': String(),
        'in': Choice(choices=['query', 'header', 'path', 'cookie']),
        'description': String(format='textarea'),
        'required': Boolean(),
        'deprecated': Boolean(),
        'allowEmptyValue': Boolean(),
        'style': String(),
        'schema': Reference('JSONSchema', definitions=definitions) | SchemaRef,
        'example': Any(),
        # TODO: Other fields
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
    required=['name', 'in']
)

definitions['RequestBody'] = Object(
    properties={
        'description': String(),
        'content': Object(additional_properties=Reference('MediaType', definitions=definitions)),
        'required': Boolean(),
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
)

definitions['Responses'] = Object(
    properties={
        'default': Reference('Response', definitions=definitions) | ResponseRef,
    },
    pattern_properties={
        '^([1-5][0-9][0-9]|[1-5]XX)$': Reference('Response', definitions=definitions) | ResponseRef,
        '^x-': Any(),
    },
    additional_properties=False,
)

definitions['Response'] = Object(
    properties={
        'description': String(),
        'content': Object(additional_properties=Reference('MediaType', definitions=definitions)),
        'headers': Object(additional_properties=Reference('Header', definitions=definitions)),
        # TODO: Header | ReferenceObject
        # TODO: links
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
)

definitions['MediaType'] = Object(
    properties={
        'schema': Reference('JSONSchema', definitions=definitions) | SchemaRef,
        'example': Any(),
        # TODO 'examples', 'encoding'
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
)

definitions['Header'] = Object(
    properties={
        'description': String(format='textarea'),
        'required': Boolean(),
        'deprecated': Boolean(),
        'allowEmptyValue': Boolean(),
        'style': String(),
        'schema': Reference('JSONSchema', definitions=definitions) | SchemaRef,
        'example': Any(),
        # TODO: Other fields
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False
)

definitions['Components'] = Object(
    properties={
        'schemas': Object(additional_properties=Reference('JSONSchema', definitions=definitions)),
        'responses': Object(additional_properties=Reference('Response', definitions=definitions)),
        'parameters': Object(additional_properties=Reference('Parameter', definitions=definitions)),
        'requestBodies': Object(additional_properties=Reference('RequestBody', definitions=definitions)),
        'securitySchemes': Object(additional_properties=Reference('SecurityScheme', definitions=definitions)),
        # TODO: Other fields
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
)

definitions['Tag'] = Object(
    properties={
        'name': String(),
        'description': String(format='textarea'),
        'externalDocs': Reference('ExternalDocumentation', definitions=definitions),
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
    required=['name']
)

definitions['SecurityRequirement'] = Object(
    additional_properties=Array(items=String()),
)

definitions['SecurityScheme'] = Object(
    properties={
        'type': Choice(choices=['apiKey', 'http', 'oauth2', 'openIdConnect']),
        'description': String(format='textarea'),
        'name': String(),
        'in': Choice(choices=['query', 'header', 'cookie']),
        'scheme': String(),
        'bearerFormat': String(),
        'flows': Any(),  # TODO: OAuthFlows
        'openIdConnectUrl': String(),
    },
    pattern_properties={
        '^x-': Any(),
    },
    additional_properties=False,
    required=['type']
)

METHODS = [
    'get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace'
]


class OpenAPICodec(BaseCodec):
    media_type = 'application/vnd.oai.openapi'
    format = 'openapi'

    def encode(self, document, **options):
        if not isinstance(document, Document):
            error = 'Document instance expected.'
            raise TypeError(error)
        definitions = Definitions('#/components/schemas/')
        paths = self.get_paths(document, definitions=definitions)
        data = self.validate_document(document, definitions, paths)
        kwargs = {
            'ensure_ascii': False,
            'indent': 4,
            'separators': (',', ': ')
        }
        return json.dumps(data, **kwargs).encode('utf-8')

    @staticmethod
    def validate_document(document, definitions, paths):
        openapi = OpenAPI.validate({
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

        if definitions:
            openapi['components'] = {'schemas': dict(definitions)}

        if not document.url:
            openapi.pop('servers')

        return openapi

    def decode(self, content, **options):
        assert isinstance(content, (str, bytes))

        if isinstance(content, bytes):
            content = content.decode('utf-8', 'ignore')

        try:
            data = json.loads(content, object_pairs_hook=dict_type)
        except ValueError as exc:
            raise exceptions.ParseError(text='Malformed JSON. %s' % exc,
                                        code='codec',
                                        key='body') from None
        return self.validate_data(data)

    def validate_data(self, data):
        data = OpenAPI.validate(data)
        title = self.lookup(data, ['info', 'title'])
        description = self.lookup(data, ['info', 'description'])
        version = self.lookup(data, ['info', 'version'])
        base_url = self.lookup(data, ['servers', 0, 'url'])
        schema_definitions = self.get_schema_definitions(data)
        content = self.get_content(data, base_url, schema_definitions)

        return Document(title=title, description=description, version=version, url=base_url, content=content)

    def get_schema_definitions(self, data):
        definitions = SchemaDefinitions()
        schemas = self.lookup(data, ['components', 'schemas'], {})
        for key, value in schemas.items():
            definitions[key] = from_json_schema(value, definitions)
        return definitions

    def get_content(self, data, base_url, schema_definitions):
        links_by_tag = dict_type()
        links = []

        for path, path_info in data.get('paths', {}).items():
            operations = {
                key: path_info[key] for key in path_info
                if key in METHODS
            }
            for operation, operation_info in operations.items():
                tag = self.lookup(operation_info, ['tags', 0])
                link = self.get_link(base_url, path, path_info, operation, operation_info, schema_definitions)
                if link is None:
                    continue

                if tag is None:
                    links.append(link)
                elif tag not in links_by_tag:
                    links_by_tag[tag] = [link]
                else:
                    links_by_tag[tag].append(link)

        sections = [
            Section(name=self.simple_slugify(tag), title=tag.title(), content=links)
            for tag, links in links_by_tag.items()
        ]

        # noinspection PyTypeChecker
        return links + sections

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

        # TODO: Handle media type generically here...
        body_schema = self.lookup(operation_info, ['requestBody', 'content', 'application/json', 'schema'])

        encoding = None
        if body_schema:
            encoding = 'application/json'
            if '$ref' in body_schema:
                ref = body_schema['$ref'][len('#/components/schemas/'):]
                schema = schema_definitions.get(ref)
                field_name = ref.lower()
            else:
                schema = from_json_schema(body_schema, schema_definitions)
                field_name = 'body'
            field_name = self.lookup(operation_info, ['requestBody', 'x-name'], default=field_name)
            fields += [Field(name=field_name, location='body', schema=schema)]

        return Link(
            name=name,
            url=urljoin(base_url, path),
            method=operation,
            title=title,
            description=description,
            fields=fields,
            encoding=encoding
        )

    @staticmethod
    def get_field(parameter, schema_definitions):
        """
        Return a single field in a link.
        """
        name = parameter.get('name')
        location = parameter.get('in')
        description = parameter.get('description')
        required = parameter.get('required', False)
        schema = parameter.get('schema')
        example = parameter.get('example')

        if schema is not None:
            if '$ref' in schema:
                ref = schema['$ref'][len('#/components/schemas/'):]
                schema = schema_definitions.get(ref)
            else:
                schema = from_json_schema(schema, schema_definitions)

        return Field(
            name=name,
            location=location,
            description=description,
            required=required,
            schema=schema,
            example=example
        )

    def get_paths(self, document, definitions=None):
        paths = dict_type()

        for link, name, sections in document.walk_links():
            path = urlparse(link.url).path
            operation_id = link.name
            tag = sections[0].name if sections else None
            method = link.method.lower()

            if path not in paths:
                paths[path] = {}
            paths[path][method] = self.get_operation(link, operation_id, tag=tag, definitions=definitions)

        return paths

    def get_operation(self, link, operation_id, tag=None, definitions=None):
        operation = {
            'operationId': operation_id
        }
        if link.title:
            operation['summary'] = link.title
        if link.description:
            operation['description'] = link.description
        if tag:
            operation['tags'] = [tag]
        if link.path_fields or link.query_fields:
            operation['parameters'] = [
                self.get_parameter(field, definitions) for field in
                link.path_fields + link.query_fields
            ]
        if link.body_field:
            schema = link.body_field.schema
            if schema is None:
                content_info = {}
            else:
                content_info = {
                    'schema': to_json_schema(schema, definitions)
                }

            operation['requestBody'] = {
                'content': {
                    link.encoding: content_info
                }
            }
        if link.response is not None:
            operation['responses'] = {
                str(link.response.status_code): {
                    'description': '',
                    'content': {
                        link.response.encoding: {
                            'schema': to_json_schema(link.response.schema, definitions)
                        }
                    }
                }
            }
        return operation

    @staticmethod
    def get_parameter(field, definitions=None):
        parameter = {
            'name': field.name,
            'in': field.location
        }
        if field.required:
            parameter['required'] = True
        if field.description:
            parameter['description'] = field.description
        if field.schema:
            parameter['schema'] = to_json_schema(field.schema, definitions)
        return parameter

    @staticmethod
    def lookup(value, keys, default=None):
        for key in keys:
            try:
                value = value[key]
            except (KeyError, IndexError, TypeError):
                return default
        return value

    @staticmethod
    def simple_slugify(text):
        if text is None:
            return None
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '_', text)
        text = re.sub(r'[_]+', '_', text)
        return text.strip('_')
