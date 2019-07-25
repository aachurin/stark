import typing
from typesystem.base import Message, ParseError, ValidationError
from typesystem.composites import NeverMatch, OneOf, AllOf, Not, IfThenElse
from typesystem.schemas import Reference as ReferenceBase, Schema as SchemaBase, SchemaDefinitions
from typesystem.json_schema import JSONSchema
from typesystem.unique import Uniqueness
from typesystem.fields import (
    Any,
    Array,
    Boolean,
    Choice,
    Const,
    Date,
    DateTime,
    Decimal,
    Field,
    Float,
    Integer,
    Number,
    Object,
    String,
    Text,
    Time,
    Union
)


__all__ = ("Message", "ParseError", "ValidationError", "NeverMatch", "OneOf", "AllOf", "Not", "IfThenElse", "Reference",
           "Schema", "SchemaDefinitions", "Any", "Array", "Boolean", "Choice", "Const", "Date", "DateTime", "Decimal",
           "Field", "Float", "Integer", "Number", "Object", "String", "Text", "Time", "Union", "UUID", "JSONSchema",
           "Uniqueness", "is_schema", "is_field")


def is_schema(arg):
    return isinstance(arg, type) and issubclass(arg, SchemaBase)


def is_field(arg):
    return isinstance(arg, Field)


def extend_option(cur_value, new_value):
    value = []
    for j in new_value:
        if j is ...:
            value += cur_value
        else:
            value += [j]
    return value


class SchemaOptions(typing.NamedTuple):
    required: tuple = ()
    read_only: tuple = ()
    strict: bool = False

    @staticmethod
    def _new(schema, new_options):
        options = schema._meta
        if hasattr(new_options, "read_only"):
            assert isinstance(new_options.read_only, list), "`read_only` option must be a list"
            read_only = extend_option(options.read_only, new_options.read_only)
        else:
            read_only = options.read_only
        if hasattr(new_options, "required"):
            assert isinstance(new_options.required, list), "`required` must be a list"
            required = extend_option(options.required, new_options.required)
        else:
            required = options.required
        conflicts = set(read_only).intersection(required)
        if conflicts:
            if hasattr(new_options, "read_only"):
                required = [field for field in required if field not in conflicts]
            else:
                read_only = [field for field in read_only if field not in conflicts]
        for field in read_only:
            assert field in schema.fields, f"No such field `{field}`."
        for field in required:
            assert field in schema.fields, f"No such field `{field}`."
        if hasattr(new_options, "strict"):
            assert isinstance(new_options.strict, bool), "`strict` must be a boolean"
            strict = new_options.strict
        else:
            strict = options.strict
        return SchemaOptions(tuple(required), tuple(read_only), strict)


class Schema(SchemaBase):

    _validator = None
    _meta: SchemaOptions = SchemaOptions()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "Meta"):
            cls._meta = SchemaOptions._new(cls, cls.Meta)
            delattr(cls, "Meta")
        cls._validator = None

    @classmethod
    def make_schema(cls) -> Field:
        # used in openapi
        return Object(
            properties=cls.fields,
            required=cls._meta.required,
            additional_properties=False if cls._meta.strict else None
        )

    @classmethod
    def make_validator(cls, *, strict: bool = False) -> Field:
        if cls._validator is None:
            fields = {k: v for k, v in cls.fields.items() if k not in cls._meta.read_only}
            cls._validator = Object(
                properties=fields,
                required=cls._meta.required,
                additional_properties=False if cls._meta.strict else None
            )
        return cls._validator


class UUID(String):
    def __init__(self, **kwargs: typing.Any) -> None:
        super().__init__(format="uuid", **kwargs)


class Reference(ReferenceBase):
    def serialize(self, obj: typing.Any) -> typing.Any:
        if obj is None:
            return None
        if not isinstance(obj, self.target):
            obj = self.target(obj)
        return dict(obj)


#
# class Lookup(Field):
#     errors = {
#         "null": "May not be null.",
#         "choice": "Not a valid choice.",
#     }
#
#     def __init__(
#         self,
#         *,
#         item: Field = None,
#         lookup: typing.Callable[[typing.Any], typing.Any] = None,
#         value: typing.Callable[[typing.Any], typing.Any] = None,
#         **kwargs: typing.Any
#     ) -> None:
#         super().__init__(**kwargs)
#         assert isinstance(item, Field), (
#             "`item` must be a field."
#         )
#         assert callable(lookup), (
#             "`lookup` must be a callable."
#         )
#         assert value is None or callable(value), (
#             "`value` must be a callable."
#         )
#         self.item = item
#         self.lookup = lookup
#         if value:
#             self.value = value
#
#     def value(self, obj):
#         return obj.id
#
#     def validate(self, value: typing.Any, *, strict: bool = False) -> typing.Any:
#         if value is None and self.allow_null:
#             return None
#         elif value is None:
#             raise self.validation_error("null")
#         # noinspection PyBroadException
#         try:
#             return self.lookup(self.item.validate(value, strict=strict))
#         except ValidationError:
#             raise
#         except Exception:
#             self.validation_error("choice")
#
#     def serialize(self, obj: typing.Any) -> typing.Any:
#         return self.item.serialize(self.value(obj))
