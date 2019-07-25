import re
import json
import typing
from stark.schema import (
    SchemaBase,
    SchemaDefinitions,
    Schema,
    is_schema,
    Field,
    Any,
    NeverMatch,
    Reference,
    String,
    Integer,
    Float,
    Decimal,
    Boolean,
    Array,
    Choice,
    Const,
    Union,
    Object,
    OneOf,
    AllOf,
    IfThenElse,
    Not
)
from stark.codecs.base import BaseCodec


class JSONSchemaCodec(BaseCodec):
    media_type = "application/schema+json"
    format = "jsonschema"

    def encode(self, item, **options):
        definitions = {}
        encoder = JSONSchemaEncoder(definitions=definitions)
        struct = encoder.encode(item)
        if definitions:
            struct["definitions"] = definitions
        indent = options.get("indent")
        if indent:
            kwargs = {
                "ensure_ascii": False,
                "indent": 4,
                "separators": (",", ":")
            }
        else:
            kwargs = {
                "ensure_ascii": False,
                "indent": None,
                "separators": (",", ":")
            }
        return json.dumps(struct, **kwargs).encode('utf-8')


class JSONSchemaEncoder:

    def __init__(self,
                 definitions: dict = None,
                 definition_base: str = "definitions"):
        self.definition_base = definition_base
        self.definitions = {} if definitions is None else definitions

    def encode(self,
               arg: typing.Union[Field, typing.Type[SchemaBase], typing.Type[Schema]]) -> typing.Union[bool, dict]:
        if isinstance(arg, Any):
            return True

        if isinstance(arg, NeverMatch):
            return False

        data: dict = {}

        if isinstance(arg, Field):
            field = arg
        elif isinstance(arg, SchemaDefinitions):
            field = None
            for key, value in field.items():
                self.definitions[key] = self.encode(value)
            return {}
        else:
            try:
                field = arg.make_schema()
            except AttributeError:
                field = arg.make_validator()

        if isinstance(field, Reference):
            data["$ref"] = f"#/{self.definition_base}/{field.target_string}"
            if field.target not in self.definitions:
                self.definitions[field.target_string] = self.encode(field.target)

        elif isinstance(field, String):
            data["type"] = ["string", "null"] if field.allow_null else "string"
            data.update(self.get_standard_properties(field))
            if field.min_length is not None or not field.allow_blank:
                data["minLength"] = field.min_length or 1
            if field.max_length is not None:
                data["maxLength"] = field.max_length
            if field.pattern_regex is not None:
                if field.pattern_regex.flags != re.RegexFlag.UNICODE:
                    flags = re.RegexFlag(field.pattern_regex.flags)
                    raise ValueError(
                        f"Cannot convert regular expression with non-standard flags "
                        f"to JSON schema: {flags!s}"
                    )
                data["pattern"] = field.pattern_regex.pattern
            if field.format is not None:
                data["format"] = field.format

        elif isinstance(field, (Integer, Float, Decimal)):
            base_type = "integer" if isinstance(field, Integer) else "number"
            data["type"] = [base_type, "null"] if field.allow_null else base_type
            data.update(self.get_standard_properties(field))
            if field.minimum is not None:
                data["minimum"] = field.minimum
            if field.maximum is not None:
                data["maximum"] = field.maximum
            if field.exclusive_minimum is not None:
                data["exclusiveMinimum"] = field.exclusive_minimum
            if field.exclusive_maximum is not None:
                data["exclusiveMaximum"] = field.exclusive_maximum
            if field.multiple_of is not None:
                data["multipleOf"] = field.multiple_of

        elif isinstance(field, Boolean):
            data["type"] = ["boolean", "null"] if field.allow_null else "boolean"
            data.update(self.get_standard_properties(field))

        elif isinstance(field, Array):
            data["type"] = ["array", "null"] if field.allow_null else "array"
            data.update(self.get_standard_properties(field))
            if field.min_items is not None:
                data["minItems"] = field.min_items
            if field.max_items is not None:
                data["maxItems"] = field.max_items
            if field.items is not None:
                if isinstance(field.items, (list, tuple)):
                    data["items"] = [self.encode(item) for item in field.items]
                else:
                    data["items"] = self.encode(field.items)
            if field.additional_items is not None:
                if isinstance(field.additional_items, bool):
                    data["additionalItems"] = field.additional_items
                else:
                    data["additionalItems"] = self.encode(field.additional_items)
            if field.unique_items is not False:
                data["uniqueItems"] = True

        elif isinstance(field, Object):
            data["type"] = ["object", "null"] if field.allow_null else "object"
            data.update(self.get_standard_properties(field))
            if field.properties:
                data["properties"] = {
                    key: self.encode(value)
                    for key, value in field.properties.items()
                }
            if field.pattern_properties:
                data["patternProperties"] = {
                    key: self.encode(value)
                    for key, value in field.pattern_properties.items()
                }
            if field.additional_properties is not None:
                if isinstance(field.additional_properties, bool):
                    data["additionalProperties"] = field.additional_properties
                else:
                    data["additionalProperties"] = self.encode(field.additional_properties)
            if field.property_names is not None:
                data["propertyNames"] = self.encode(field.property_names)
            if field.max_properties is not None:
                data["maxProperties"] = field.max_properties
            if field.min_properties is not None:
                data["minProperties"] = field.min_properties
            if field.required:
                data["required"] = field.required
            if is_schema(arg) and hasattr(arg, '_meta'):
                if arg._meta.read_only:
                    for key in arg._meta.read_only:
                        if key in data["properties"]:
                            data["properties"][key]["readOnly"] = True
        elif isinstance(field, Choice):
            data["enum"] = [key for key, value in field.choices]
            data["enumNames"] = [value for key, value in field.choices]
            data.update(self.get_standard_properties(field))

        elif isinstance(field, Const):
            data["const"] = field.const
            data.update(self.get_standard_properties(field))

        elif isinstance(field, Union):
            data["anyOf"] = [
                self.encode(item) for item in field.any_of
            ]
            data.update(self.get_standard_properties(field))

        elif isinstance(field, OneOf):
            data["oneOf"] = [
                self.encode(item) for item in field.one_of
            ]
            data.update(self.get_standard_properties(field))

        elif isinstance(field, AllOf):
            data["allOf"] = [
                self.encode(item) for item in field.all_of
            ]
            data.update(self.get_standard_properties(field))

        elif isinstance(field, IfThenElse):
            data["if"] = self.encode(field.if_clause)
            if field.then_clause is not None:
                data["then"] = self.encode(field.then_clause)
            if field.else_clause is not None:
                data["else"] = self.encode(field.else_clause)
            data.update(self.get_standard_properties(field))

        elif isinstance(field, Not):
            data["not"] = self.encode(field.negated)
            data.update(self.get_standard_properties(field))

        elif field is not None:
            name = type(field).__qualname__
            raise ValueError(f"Cannot convert field type {name!r} to JSON Schema")

        return data

    @staticmethod
    def get_standard_properties(field: Field) -> dict:
        data = {}
        if field.has_default():
            data["default"] = field.default
        if field.title:
            data["title"] = field.title
        if field.description:
            data["description"] = field.description
        return data
