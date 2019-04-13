import inspect
import re
import typing
import datetime
import decimal
from stark import http, schemas
from stark.document import Document, Field, Link, Response, Section


PRIMITIVES = {
    inspect.Parameter.empty: schemas.Any,
    int: schemas.Integer,
    float: schemas.Float,
    str: schemas.String,
    bool: schemas.Boolean,
    datetime.datetime: schemas.DateTime,
    datetime.date: schemas.Date,
    datetime.time: schemas.Time,
    decimal.Decimal: schemas.Decimal
}


class Route:
    def __init__(self, url, method, handler, name=None, documented=True, standalone=False):
        self.url = url
        self.method = method
        self.handler = handler
        self.name = name or handler.__name__
        self.documented = documented
        self.standalone = standalone
        self.link = self.generate_link(url, method, handler, self.name)

    def generate_link(self, url, method, handler, name):
        fields = self.generate_fields(url, method, handler)
        response = self.generate_response(handler)
        encoding = None
        if any([f.location == 'body' for f in fields]):
            encoding = 'application/json'
        return Link(
            url=url,
            method=method,
            name=name,
            encoding=encoding,
            fields=fields,
            response=response,
            description=handler.__doc__
        )

    @staticmethod
    def generate_fields(url, method, handler):
        fields = []
        path_names = [
            item.strip('{}').lstrip('+') for item in re.findall('{[^}]*}', url)
        ]
        parameters = inspect.signature(handler).parameters
        for name, param in parameters.items():
            if name in path_names:
                try:
                    schema = PRIMITIVES[param.annotation]
                except KeyError:
                    msg = "Unsupported annotation %r for path parameter %r"
                    raise TypeError(msg % (param.annotation, name))
                field = Field(name=name, location='path', schema=schema())
                fields.append(field)
            elif param.annotation in PRIMITIVES or param.annotation is http.QueryParam:
                schema = PRIMITIVES.get(param.annotation, schemas.String)
                if param.default is param.empty:
                    kwargs = {}
                elif param.default is None:
                    kwargs = {'default': None, 'allow_null': True}
                else:
                    kwargs = {'default': param.default}
                field = Field(name=name, location='query', schema=schema(**kwargs))
                fields.append(field)
            elif isinstance(param.annotation, type) and issubclass(param.annotation, schemas.SchemaBase):
                if method in ('GET', 'DELETE'):
                    for field_name, field_value in param.annotation.fields.items():
                        field = Field(name=field_name, location='query', schema=field_value)
                        fields.append(field)
                else:
                    field = Field(name=name, location='body', schema=param.annotation)
                    fields.append(field)
        return fields

    def generate_response(self, handler):
        annotation = inspect.signature(handler).return_annotation
        annotation = self.coerce_generics(annotation)
        if ((isinstance(annotation, type) and issubclass(annotation, schemas.SchemaBase))
                or isinstance(annotation, schemas.Field)):
            return Response(encoding='application/json', status_code=200, schema=annotation)

    def coerce_generics(self, annotation):
        origin = getattr(annotation, '__origin__', annotation)

        if origin is typing.Union:
            args = [self.coerce_generics(x) for x in annotation.__args__]
            any_of = []
            for arg in args:
                if isinstance(arg, schemas.Field):
                    any_of.append(arg)
                elif isinstance(arg, type) and issubclass(arg, schemas.SchemaBase):
                    any_of.append(schemas.Reference(to=arg))
                else:
                    return
            return schemas.Union(any_of=any_of)

        if isinstance(origin, type) and issubclass(origin, schemas.SchemaBase):
            return origin

        if isinstance(origin, type) and issubclass(origin, typing.Sequence):
            args = getattr(annotation, '__args__', None)
            if args:
                arg = self.coerce_generics(args[0])
                if isinstance(arg, schemas.Field):
                    return schemas.Array(items=arg)
                if isinstance(arg, type) and issubclass(arg, schemas.SchemaBase):
                    return schemas.Array(items=schemas.Reference(to=arg))
            return schemas.Array(items=schemas.Any())

        if isinstance(origin, type) and issubclass(origin, typing.Mapping):
            args = getattr(annotation, '__args__', None)
            if args:
                arg = self.coerce_generics(args[1])
                if isinstance(arg, schemas.Field):
                    return schemas.Object(additional_properties=arg)
                if isinstance(arg, type) and issubclass(arg, schemas.SchemaBase):
                    return schemas.Object(additional_properties=schemas.Reference(to=arg))
            return schemas.Object(additional_properties=True)

        field = PRIMITIVES.get(annotation)
        if field:
            return field()


class Include:
    def __init__(self, url, name, routes, documented=True):
        self.url = url
        self.name = name
        self.routes = routes
        self.documented = documented
        self.section = self.generate_section(routes, name)

    def generate_section(self, routes, name):
        content = self.generate_content(routes)
        return Section(name=name, content=content)

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
    return Document(content=content)
