import inspect
import re
import typing
import datetime
import decimal
import uuid
from stark import http, document, exceptions
from stark.server.utils import import_path
from stark.server.docstrings import parse_docstring
from stark.schema import (
    is_field,
    is_schema,
    Any,
    Array,
    Boolean,
    Date,
    DateTime,
    Decimal,
    Float,
    Integer,
    Object,
    String,
    Time,
    UUID,
    Union,
    Reference
)


class Settings:

    ROUTES = "routes"
    SCHEMA_URL = "/schema"
    DOCS_URL = "/docs/"
    STATIC_URL = "/static/"
    DOCS_THEME = "apistar"
    LOGGING = None
    COMPONENTS = ()
    TEMPLATE_DIRS = ()
    STATIC_DIRS = ()

    def __init__(self, mod):
        tuple_settings = [
            "COMPONENTS",
            "TEMPLATE_DIRS",
            "STATIC_DIRS",
        ]
        for setting in dir(mod):
            if setting.isupper():
                setting_value = getattr(mod, setting)
                if (setting in tuple_settings and
                        not isinstance(setting_value, (list, tuple))):
                    msg = f"The {setting} setting must be a list or a tuple."
                    raise exceptions.ConfigurationError(msg)
                setattr(self, setting, setting_value)


PRIMITIVES = {
    inspect.Parameter.empty: Any,
    int: Integer,
    float: Float,
    str: String,
    bool: Boolean,
    datetime.datetime: DateTime,
    datetime.date: Date,
    datetime.time: Time,
    decimal.Decimal: Decimal,
    uuid.UUID: UUID
}


class Route:
    def __init__(self,
                 url: str,
                 method: str,
                 handler: typing.Union[str, typing.Callable],
                 name: str = None,
                 documented: bool = True,
                 standalone: bool = False,
                 tags: typing.Sequence[str] = None):
        if isinstance(handler, str):
            handler = import_path(handler)
        self.url = url
        self.method = method
        self.handler = handler
        self.name = name or handler.__name__
        self.documented = documented
        self.standalone = standalone
        self.link = self.generate_link(url, method, handler, self.name, tags)

    def generate_link(self, url, method, handler, name, tags):
        description = parse_docstring(handler.__doc__)
        fields = self.generate_fields(url, method, handler, description["params"])
        response = self.generate_response(handler)
        encoding = None
        if any([f.location == "body" for f in fields]):
            encoding = "application/json"
        return document.Link(
            url=url,
            method=method,
            name=name,
            encoding=encoding,
            fields=fields,
            response=response,
            description=description["short_description"],
            tags=tags
        )

    def generate_fields(self, url, method, handler, description):
        fields = []
        path_names = [
            item.strip("{}").lstrip("+") for item in re.findall("{[^}]*}", url)
        ]
        body_params = []
        parameters = inspect.signature(handler).parameters
        for name, param in parameters.items():
            if name in path_names:
                fields.append(self.generate_path_field(param, description.get(name, "")))
            elif (param.annotation in PRIMITIVES
                  or param.annotation is http.QueryParam
                  or hasattr(param.annotation, "__schema__")):
                fields += self.generate_query_fields(param, description.get(name, ""))
            elif is_schema(param.annotation) and method in ("GET", "DELETE"):
                fields += self.generate_query_fields_from_schema(param)
            elif is_schema(param.annotation):
                fields.append(document.Field(name=name, location="body", schema=param.annotation))
                body_params.append(param)
        if len(body_params) > 1:
            params = "\n  ".join(f"{x.name}: {x.annotation.__name__}" for x in body_params)
            msg = (
                f"\n\nUsing multiple body fields in {method} handler "
                f"`{handler.__module__}.{handler.__name__}` is confusing.\n"
                f"Use only one of the following parameters:\n  {params}\n"
            )
            raise exceptions.ConfigurationError(msg)
        return fields

    @staticmethod
    def generate_path_field(param, description):
        schema = None
        try:
            schema = PRIMITIVES[param.annotation](description=description)
        except KeyError:
            if isinstance(param.annotation, type) and hasattr(param.annotation, "__schema__"):
                schema = param.annotation.__schema__()
            if not is_field(schema):
                raise TypeError(
                    f"Unsupported annotation {param.annotation} for path parameter `{param.name}`"
                )
        return document.Field(name=param.name, location="path", schema=schema)

    @staticmethod
    def generate_query_fields(param, description):
        schema = None
        if hasattr(param.annotation, "__schema__"):
            schema = param.annotation.__schema__()
        if isinstance(schema, (list, tuple)):
            schema = dict(schema)
        if isinstance(schema, typing.Mapping):
            return [
                document.Field(name=name, location="query", schema=field)
                for name, field in schema.items()
            ]
        if schema is None and (param.annotation in PRIMITIVES or param.annotation is http.QueryParam):
            schema = PRIMITIVES.get(param.annotation, String)
        if not schema:
            raise TypeError(
                f"Unsupported annotation {param.annotation} for query parameter `{param.name}`"
            )
        required = False
        if isinstance(schema, type):
            if param.default is param.empty:
                required = True
                kwargs = {}
            elif param.default is None:
                kwargs = {"default": None, "allow_null": True}
            else:
                kwargs = {"default": param.default}
            schema = schema(description=description, **kwargs)
        return [document.Field(name=param.name, location="query", required=required, schema=schema)]

    @staticmethod
    def generate_query_fields_from_schema(param):
        schema = param.annotation.make_validator()
        return [
            document.Field(name=name, location="query", required=(name in schema.required), schema=field)
            for name, field in schema.properties.items()
        ]

    def generate_response(self, handler):
        annotation = inspect.signature(handler).return_annotation
        annotation = self.coerce_generics(annotation)
        if is_schema(annotation) or is_field(annotation):
            return document.Response(encoding="application/json", status_code=200, schema=annotation)

    def coerce_generics(self, annotation):
        origin = getattr(annotation, "__origin__", annotation)

        if is_schema(origin):
            return origin

        if origin is typing.Union:
            args = [self.coerce_generics(x) for x in annotation.__args__]
            any_of = [arg for arg in args if is_field(arg) or is_schema(arg)]
            return Union(any_of=any_of)

        if isinstance(origin, type):
            if issubclass(origin, typing.List):
                if hasattr(annotation, "__args__"):
                    arg = self.coerce_generics(annotation.__args__[0])
                    if is_schema(arg):
                        arg = Reference(to=arg)
                    if is_field(arg):
                        return Array(items=arg)
                return Array()
            elif issubclass(origin, typing.Tuple):
                if hasattr(annotation, "__args__"):
                    args = annotation.__args__
                    if len(args) == 2 and args[1] is ...:
                        arg = self.coerce_generics(annotation.__args__[0])
                        if is_schema(arg):
                            arg = Reference(to=arg)
                        if is_field(arg):
                            return Array(items=arg)
                    else:
                        args = [self.coerce_generics(arg) for arg in args]
                        args = [
                            Reference(arg) if is_schema(arg) else arg
                            for arg in args if is_field(arg) or is_schema(arg)
                        ]
                        if args:
                            return Array(items=args)
                return Array()
            elif issubclass(origin, typing.Mapping):
                if hasattr(annotation, "__args__"):
                    arg = self.coerce_generics(annotation.__args__[1])
                    if is_schema(arg):
                        arg = Reference(to=arg)
                    if is_field(arg):
                        return Object(additional_properties=arg)
                return Object(additional_properties=True)
        else:
            try:
                return PRIMITIVES[annotation]()
            except KeyError:
                pass


class Include:
    def __init__(self, url, name, routes, documented=True):
        if isinstance(routes, str):
            routes = import_path([routes + ".routes", routes])
        self.url = url
        self.name = name
        self.routes = routes
        self.documented = documented
        self.section = self.generate_section(routes, name)

    def generate_section(self, routes, name):
        content = self.generate_content(routes)
        return document.Section(name=name, content=content)

    @staticmethod
    def generate_content(routes):
        content = []
        for item in routes:
            if isinstance(item, Route):
                if item.link is not None:
                    content.append(item.link)
            elif isinstance(item, Include):
                if item.section is not None:
                    content.append(item.section)
        return content


def generate_document(routes):
    content = []
    for item in routes:
        if isinstance(item, Route) and item.documented:
            content.append(item.link)
        elif isinstance(item, Include) and item.documented:
            content.append(item.section)
            for link in item.section.get_links():
                link.url = item.url + link.url
    return document.Document(content=content)
