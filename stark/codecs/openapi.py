import json
from urllib.parse import urlparse
from stark.codecs import BaseCodec
from stark.codecs.jsonschema import JSONSchemaEncoder
from stark.schema import (
    SchemaDefinitions,
    JSONSchema,
    String,
    Choice,
    Object,
    Any,
    Reference,
    Array,
    Boolean,
    is_schema
)
from stark.compat import dict_type
from stark.document import Document


SchemaRef = Object(
    properties={"$ref": String(pattern="^#/components/schemas/")}
)

RequestBodyRef = Object(
    properties={"$ref": String(pattern="^#/components/requestBodies/")}
)

ResponseRef = Object(
    properties={"$ref": String(pattern="^#/components/responses/")}
)

openapi_definitions = SchemaDefinitions()

OpenAPI = Object(
    title="OpenAPI",
    properties={
        "openapi": String(),
        "info": Reference("Info", definitions=openapi_definitions),
        "servers": Array(items=Reference("Server", definitions=openapi_definitions)),
        "paths": Reference("Paths", definitions=openapi_definitions),
        "components": Reference("Components", definitions=openapi_definitions),
        "security": Array(items=Reference("SecurityRequirement", definitions=openapi_definitions)),
        "tags": Array(items=Reference("Tag", definitions=openapi_definitions)),
        "externalDocs": Reference("ExternalDocumentation", definitions=openapi_definitions),
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
    required=["openapi", "info", "paths"]
)

openapi_definitions["JSONSchema"] = JSONSchema

openapi_definitions["Info"] = Object(
    properties={
        "title": String(allow_blank=True),
        "description": String(format="textarea", allow_blank=True),
        "termsOfService": String(format="url", allow_blank=True),
        "contact": Reference("Contact", definitions=openapi_definitions),
        "license": Reference("License", definitions=openapi_definitions),
        "version": String(allow_blank=True),
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
    required=["title", "version"]
)

openapi_definitions["Contact"] = Object(
    properties={
        "name": String(),
        "url": String(format="url"),
        "email": String(format="email"),
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
)

openapi_definitions["License"] = Object(
    properties={
        "name": String(),
        "url": String(format="url"),
    },
    required=["name"],
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
)

openapi_definitions["Server"] = Object(
    properties={
        "url": String(allow_blank=True),
        "description": String(format="textarea"),
        "variables": Object(additional_properties=Reference("ServerVariable", definitions=openapi_definitions)),
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
    required=["url"]
)

openapi_definitions["ServerVariable"] = Object(
    properties={
        "enum": Array(items=String()),
        "default": String(),
        "description": String(format="textarea"),
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
    required=["default"]
)

openapi_definitions["Paths"] = Object(
    pattern_properties={
        "^/": Reference("Path", definitions=openapi_definitions),
        "^x-": Any(),
    },
    additional_properties=False,
)

openapi_definitions["Path"] = Object(
    properties={
        "summary": String(),
        "description": String(format="textarea"),
        "get": Reference("Operation", definitions=openapi_definitions),
        "put": Reference("Operation", definitions=openapi_definitions),
        "post": Reference("Operation", definitions=openapi_definitions),
        "delete": Reference("Operation", definitions=openapi_definitions),
        "options": Reference("Operation", definitions=openapi_definitions),
        "head": Reference("Operation", definitions=openapi_definitions),
        "patch": Reference("Operation", definitions=openapi_definitions),
        "trace": Reference("Operation", definitions=openapi_definitions),
        "servers": Array(items=Reference("Server", definitions=openapi_definitions)),
        "parameters": Array(items=Reference("Parameter", definitions=openapi_definitions))  # TODO: | ReferenceObject
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
)

openapi_definitions["Operation"] = Object(
    properties={
        "tags": Array(items=String()),
        "summary": String(),
        "description": String(format="textarea"),
        "externalDocs": Reference("ExternalDocumentation", definitions=openapi_definitions),
        "operationId": String(),
        "parameters": Array(items=Reference("Parameter", definitions=openapi_definitions)),
        # TODO: | ReferenceObject
        "requestBody": RequestBodyRef | Reference("RequestBody", definitions=openapi_definitions),
        # TODO: RequestBody | ReferenceObject
        "responses": Reference("Responses", definitions=openapi_definitions),
        # TODO: "callbacks"
        "deprecated": Boolean(),
        "security": Array(Reference("SecurityRequirement", definitions=openapi_definitions)),
        "servers": Array(items=Reference("Server", definitions=openapi_definitions)),
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
)

openapi_definitions["ExternalDocumentation"] = Object(
    properties={
        "description": String(format="textarea"),
        "url": String(format="url"),
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
    required=["url"]
)

openapi_definitions["Parameter"] = Object(
    properties={
        "name": String(),
        "in": Choice(choices=["query", "header", "path", "cookie"]),
        "description": String(format="textarea"),
        "required": Boolean(),
        "deprecated": Boolean(),
        "allowEmptyValue": Boolean(),
        "style": String(),
        "schema": Reference("JSONSchema", definitions=openapi_definitions) | SchemaRef,
        "example": Any(),
        # TODO: Other fields
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
    required=["name", "in"]
)

openapi_definitions["RequestBody"] = Object(
    properties={
        "description": String(),
        "content": Object(additional_properties=Reference("MediaType", definitions=openapi_definitions)),
        "required": Boolean(),
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
)

openapi_definitions["Responses"] = Object(
    properties={
        "default": Reference("Response", definitions=openapi_definitions) | ResponseRef,
    },
    pattern_properties={
        "^([1-5][0-9][0-9]|[1-5]XX)$": Reference("Response", definitions=openapi_definitions) | ResponseRef,
        "^x-": Any(),
    },
    additional_properties=False,
)

openapi_definitions["Response"] = Object(
    properties={
        "description": String(),
        "content": Object(additional_properties=Reference("MediaType", definitions=openapi_definitions)),
        "headers": Object(additional_properties=Reference("Header", definitions=openapi_definitions)),
        # TODO: Header | ReferenceObject
        # TODO: links
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
)

openapi_definitions["MediaType"] = Object(
    properties={
        "schema": Reference("JSONSchema", definitions=openapi_definitions) | SchemaRef,
        "example": Any(),
        # TODO "examples", "encoding"
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
)

openapi_definitions["Header"] = Object(
    properties={
        "description": String(format="textarea"),
        "required": Boolean(),
        "deprecated": Boolean(),
        "allowEmptyValue": Boolean(),
        "style": String(),
        "schema": Reference("JSONSchema", definitions=openapi_definitions) | SchemaRef,
        "example": Any(),
        # TODO: Other fields
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False
)

openapi_definitions["Components"] = Object(
    properties={
        "schemas": Object(additional_properties=Reference("JSONSchema", definitions=openapi_definitions)),
        "responses": Object(additional_properties=Reference("Response", definitions=openapi_definitions)),
        "parameters": Object(additional_properties=Reference("Parameter", definitions=openapi_definitions)),
        "requestBodies": Object(additional_properties=Reference("RequestBody", definitions=openapi_definitions)),
        "securitySchemes": Object(additional_properties=Reference("SecurityScheme", definitions=openapi_definitions)),
        # TODO: Other fields
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
)

openapi_definitions["Tag"] = Object(
    properties={
        "name": String(),
        "description": String(format="textarea"),
        "externalDocs": Reference("ExternalDocumentation", definitions=openapi_definitions),
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
    required=["name"]
)

openapi_definitions["SecurityRequirement"] = Object(
    additional_properties=Array(items=String()),
)

openapi_definitions["SecurityScheme"] = Object(
    properties={
        "type": Choice(choices=["apiKey", "http", "oauth2", "openIdConnect"]),
        "description": String(format="textarea"),
        "name": String(),
        "in": Choice(choices=["query", "header", "cookie"]),
        "scheme": String(),
        "bearerFormat": String(),
        "flows": Any(),  # TODO: OAuthFlows
        "openIdConnectUrl": String(),
    },
    pattern_properties={
        "^x-": Any(),
    },
    additional_properties=False,
    required=["type"]
)

METHODS = [
    "get", "put", "post", "delete", "options", "head", "patch", "trace"
]


class OpenAPICodec(BaseCodec):
    media_type = "application/vnd.oai.openapi"
    format = "openapi"

    def encode(self, document, **options):
        if not isinstance(document, Document):
            error = "Document instance expected."
            raise TypeError(error)

        definitions = {}
        codec = JSONSchemaEncoder(
            definitions,
            definition_base="components/schemas"
        )
        paths = self.get_paths(document, codec=codec)
        data = self.validate_document(document, definitions, paths)
        kwargs = {
            "ensure_ascii": False,
            "indent": 4,
            "separators": (",", ": ")
        }
        return json.dumps(data, **kwargs).encode("utf-8")

    @staticmethod
    def validate_document(document, definitions, paths):
        openapi = OpenAPI.validate({
            "openapi": "3.0.0",
            "info": {
                "version": document.version,
                "title": document.title,
                "description": document.description
            },
            "servers": [{
                "url": document.url
            }],
            "paths": paths
        })

        if definitions:
            openapi["components"] = {"schemas": dict(definitions)}

        if not document.url:
            openapi.pop("servers")

        return openapi

    def get_paths(self, document, codec):
        paths = dict_type()

        for link, name, sections in document.walk_links():
            path = urlparse(link.url).path
            operation_id = link.name
            method = link.method.lower()

            if path not in paths:
                paths[path] = {}
            paths[path][method] = self.get_operation(link, operation_id, codec)

        return paths

    def get_operation(self, link, operation_id, codec):
        operation = {
            "operationId": operation_id
        }
        if link.title:
            operation["summary"] = link.title
        if link.description:
            operation["description"] = link.description
        tags = link.tags if link.tags else []
        if tags:
            operation["tags"] = tags
        if link.path_fields or link.query_fields:
            operation["parameters"] = [
                self.get_parameter(field, codec) for field in
                link.path_fields + link.query_fields
            ]
        if link.body_field:
            schema = link.body_field.schema
            if schema is None:
                content_info = {}
            else:
                content_info = {
                    "schema": codec.encode(Reference(to=schema))
                }
            operation["requestBody"] = {
                "content": {
                    link.encoding: content_info
                }
            }
        if link.response is not None:
            schema = link.response.schema
            if is_schema(schema):
                schema = Reference(to=schema)
            response = {
                "description": "",
            }
            if schema is not None:
                response["content"] = {
                    link.response.encoding: {
                        "schema": codec.encode(schema)
                    }
                }
            operation["responses"] = {
                str(link.response.status_code): response
            }
        return operation

    @staticmethod
    def get_parameter(field, codec):
        parameter = {
            "name": field.name,
            "in": field.location
        }
        if field.required:
            parameter["required"] = True
        if field.description:
            parameter["description"] = field.description
        if field.schema:
            parameter["schema"] = codec.encode(field.schema)
        return parameter
