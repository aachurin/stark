import inspect
import re
import typing
import datetime
import decimal
import uuid
from stark import http, document, exceptions
from stark.server.utils import import_path, parse_docstring
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


def issubclass_safe(cls, classinfo):
    try:
        return issubclass(cls, classinfo)
    except TypeError:
        return False


class Route:
    link = None

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
        self.tags = tags

    def setup(self, injector):
        self.link = LinkGenerator(injector).generate_link(
            self.url,
            self.method,
            self.handler,
            self.name,
            self.tags
        )


class Include:

    section = None

    def __init__(self, url, name, routes, documented=True):
        if isinstance(routes, str):
            routes = import_path(routes, ["routes", "ROUTES"])
        self.url = url
        self.name = name
        self.routes = routes
        self.documented = documented

    def setup(self, injector):
        content = []
        for item in self.routes:
            item.setup(injector)
            if isinstance(item, Route):
                content.append(item.link)
            elif isinstance(item, Include):
                content.append(item.section)
        self.section = document.Section(name=self.name, content=content)


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


class LinkGenerator:

    def __init__(self, injector):
        self.injector = injector

    def generate_link(self, url, method, handler, name, tags):
        docstring = parse_docstring(handler.__doc__)
        fields = self.generate_fields(url, method, handler)
        response = self.generate_response(handler)
        encoding = None
        if any([f.location == "body" for f in fields]):
            encoding = "application/json"
        description = (docstring.short_description + "\n" + docstring.long_description).strip()
        return document.Link(
            url=url,
            method=method,
            name=name,
            encoding=encoding,
            fields=fields,
            response=response,
            description=description,
            tags=tags
        )

    def generate_fields(self, url, method, handler):
        fields = []
        path_names = [
            item.strip("{}").lstrip("+") for item in re.findall("{[^}]*}", url)
        ]
        body_params = []
        parameters = self.injector.resolve_validation_parameters(handler)
        for name, param in parameters.items():
            if name in path_names:
                fields.append(self.generate_path_field(param))
            elif is_schema(param.annotation):
                if method in ("GET", "DELETE"):
                    fields += self.generate_query_fields_from_schema(param)
                else:
                    fields.append(document.Field(name=name, location="body", schema=param.annotation))
                    body_params.append(param)
            else:
                fields += self.generate_query_fields(param)

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
    def generate_path_field(param):
        try:
            schema = PRIMITIVES[param.annotation](description=param.description)
        except KeyError:
            raise TypeError(
                f"Annotation {param.annotation} is not suitable for path parameter `{param.name}`"
            )
        return document.Field(name=param.name, location="path", schema=schema)

    @staticmethod
    def generate_query_fields(param):
        t = param.annotation
        kwargs = {"description": param.description}
        if t in PRIMITIVES:
            schema = PRIMITIVES[t]
        else:
            o = getattr(t, "__origin__", t)
            try:
                generic = issubclass(o, (typing.Sequence, typing.Set, typing.Tuple))
            except TypeError:
                generic = False
            if generic:
                schema = Array
                if issubclass(o, typing.Tuple):
                    if hasattr(t, "__args__") and not t._special:
                        if len(t.__args__) == 2 and t.__args__[1] is ...:
                            try:
                                kwargs["items"] = PRIMITIVES[t.__args__[0]]()
                            except KeyError:
                                raise TypeError(
                                    f"Annotation `{param.name}: {param.annotation}` is not allowed"
                                )
                        else:
                            try:
                                kwargs["items"] = [PRIMITIVES[arg]() for arg in t.__args__]
                            except KeyError:
                                raise TypeError(
                                    f"Annotation `{param.name}: {param.annotation}` is not allowed"
                                )
                else:
                    kwargs["unique_items"] = issubclass(o, typing.Set)
                    if hasattr(t, "__args__") and not t._special:
                        try:
                            kwargs["items"] = PRIMITIVES[t.__args__[0]]()
                        except KeyError:
                            raise TypeError(
                                f"Annotation `{param.name}: {param.annotation}` is not allowed"
                            )
            else:
                return []

        required = False
        if param.default is param.empty:
            required = True
        elif param.default is None:
            kwargs["default"] = None
            kwargs["allow_null"] = True
        else:
            kwargs["default"] = param.default
        schema = schema(**kwargs)
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
        if annotation in (None, inspect.Signature.empty):
            return document.Response(encoding="application/json", status_code=204)
        annotation = self.coerce_generics(annotation)
        return document.Response(encoding="application/json", status_code=200, schema=annotation)

    def coerce_generics(self, t):
        if is_schema(t):
            return t
        if t in PRIMITIVES:
            return PRIMITIVES[t]()

        o = getattr(t, "__origin__", t)
        if o is typing.Union:
            args = [self.coerce_generics(x) for x in t.__args__]
            return Union(any_of=args)
        if issubclass(o, (typing.Sequence, typing.Set)):
            unique_items = issubclass(o, typing.Set)
            if hasattr(t, "__args__") and not t._special:
                arg = self.coerce_generics(t.__args__[0])
                return Array(items=Reference(to=arg) if is_schema(arg) else arg,
                             unique_items=unique_items)
            else:
                return Array(unique_items=unique_items)
        elif issubclass(o, typing.Mapping):
            if hasattr(t, "__args__") and not t._special:
                arg = self.coerce_generics(t.__args__[1])
                return Object(additional_properties=Reference(to=arg) if is_schema(arg) else arg)
            else:
                return Object(additional_properties=True)
        elif issubclass(o, typing.Tuple):
            if hasattr(t, "__args__") and not t._special:
                if len(t.__args__) == 2 and t.__args__[1] is ...:
                    arg = self.coerce_generics(t.__args__[0])
                    return Array(items=Reference(to=arg) if is_schema(arg) else arg)
                else:
                    args = [
                        (Reference(x) if is_schema(x) else x)
                        for x in [self.coerce_generics(arg) for arg in t.__args__]
                    ]
                    return Array(items=args)
            else:
                return Array()
        return Any()


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
