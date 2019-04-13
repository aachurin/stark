import importlib.util
from typesystem.fields import (
    Any,
    Array,
    Boolean,
    Choice,
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
    Union,
    Const
)
from typesystem.schemas import Reference, SchemaDefinitions, Schema as SchemaBase

__all__ = ('Any', 'Array', 'Boolean', 'Choice', 'Date', 'DateTime', 'Decimal', 'Field', 'Float', 'Integer',
           'Number', 'Object', 'String', 'Text', 'Time', 'Union', 'Const', 'Reference', 'Schema',
           'SchemaDefinitions', 'to_json_schema', 'from_json_schema')


def apply_meta(schema, meta):
    options = {
        'required': '_required_fields',
        'read_only': '_read_only_fields',
        'write_only': '_write_only_fields',
    }
    for option, attr in options.items():
        current_value = getattr(schema, attr, None)
        new_value = getattr(meta, option, None)
        if new_value is not None and not isinstance(new_value, list):
            msg = '%r must be a list'
            raise TypeError(msg % option)
        if new_value is None:
            if current_value is None:
                if option == 'required':
                    new_value = [key for key, value in schema.fields.items() if not value.has_default()]
                else:
                    new_value = []
            else:
                new_value = current_value
        value = []
        for i, j in enumerate(new_value):
            if j is ...:
                value += current_value
            else:
                value += [j]
        if len(set(value)) != len(value):
            raise TypeError('Each item in %r must be unique' % option)
        setattr(schema, attr, value)


class Schema(SchemaBase):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        apply_meta(cls, getattr(cls, 'Meta', None))
        if hasattr(cls, 'Meta'):
            del cls.Meta

    @classmethod
    def make_validator(cls, *, strict: bool = False) -> Field:
        return Object(
            properties=cls.fields,
            required=cls._required_fields,
            additional_properties=False if strict else None,
        )


spec = importlib.util.find_spec('typesystem.json_schema')
json_schema = importlib.util.module_from_spec(spec)
spec.loader.exec_module(json_schema)
del spec

JSONSchema = json_schema.JSONSchema
from_json_schema = json_schema.from_json_schema


class Definitions(dict):
    __slots__ = ('base',)

    def __init__(self, base):
        self.base = base


def to_json_schema(arg, definitions=None):
    if definitions is None:
        is_root = True
        definitions = Definitions('#/definitions/')
    else:
        assert isinstance(definitions, Definitions)
        is_root = False
    data = _to_json_schema(arg, _definitions=definitions)
    if is_root and definitions:
        data['definitions'] = definitions
    return data


def _to_json_schema(arg, _definitions, _to_json_schema=json_schema.to_json_schema):
    if isinstance(arg, Reference):
        _definitions[arg.target_string] = _to_json_schema(arg.target, _definitions=_definitions)
        return {'$ref': _definitions.base + arg.target_string}

    if isinstance(arg, type) and issubclass(arg, SchemaBase):
        _definitions[arg.__name__] = _to_json_schema(arg.make_validator(), _definitions=_definitions)
        return {'$ref': _definitions.base + arg.__name__}

    return _to_json_schema(arg, _definitions=_definitions)


def _get_standard_properties(field: Field) -> dict:
    data = {}
    if field.has_default():
        data['default'] = field.default
    if field.title:
        data['title'] = field.title
    if field.description:
        data['description'] = field.description
    return data


json_schema.get_standard_properties = _get_standard_properties
json_schema.to_json_schema = _to_json_schema
