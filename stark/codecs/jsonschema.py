from apistar.schemas.jsonschema import JSONSchema
from stark.codecs.base import BaseCodec


class JSONSchemaCodec(JSONSchema, BaseCodec):

    media_type = 'application/schema+json'
