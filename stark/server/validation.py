import inspect
import typing
import datetime
import decimal
from stark import codecs, exceptions, http, schemas
from stark.conneg import negotiate_content_type
from stark.server.components import Component
from stark.server.core import Route

ValidatedPathParams = typing.NewType('ValidatedPathParams', dict)
ValidatedQueryParams = typing.NewType('ValidatedQueryParams', dict)
ValidatedRequestData = typing.TypeVar('ValidatedRequestData')


class RequestDataComponent(Component):
    def __init__(self):
        self.codecs = [
            codecs.JSONCodec(),
            codecs.URLEncodedCodec(),
            codecs.MultiPartCodec(),
        ]

    def can_handle_parameter(self, parameter: inspect.Parameter):
        return parameter.annotation is http.RequestData

    def resolve(self,
                content: http.Body,
                headers: http.Headers):
        if not content:
            return None

        content_type = headers.get('Content-Type')

        try:
            codec = negotiate_content_type(self.codecs, content_type)
        except exceptions.NoCodecAvailable:
            raise exceptions.UnsupportedMediaType()

        try:
            return codec.decode(content, headers=headers)
        except exceptions.ValidationError as exc:
            raise exceptions.BadRequest(dict(exc))


class ValidatePathParamsComponent(Component):
    def resolve(self,
                route: Route,
                path_params: http.PathParams) -> ValidatedPathParams:
        path_fields = route.link.path_fields
        validator = schemas.Object(
            properties={field.name: field.schema for field in path_fields},
            required=[field.name for field in path_fields]
        )
        try:
            return validator.validate(path_params)
        except exceptions.ValidationError as exc:
            raise exceptions.NotFound(dict(exc))


class ValidateQueryParamsComponent(Component):
    def resolve(self,
                route: Route,
                query_params: http.QueryParams) -> ValidatedQueryParams:
        query_fields = route.link.query_fields
        validator = schemas.Object(
            properties={field.name: field.schema for field in query_fields},
            required=[field.name for field in query_fields if field.required]
        )
        try:
            return validator.validate(query_params)
        except exceptions.ValidationError as exc:
            raise exceptions.BadRequest(dict(exc))


class ValidateRequestDataComponent(Component):
    def can_handle_parameter(self, parameter: inspect.Parameter):
        return parameter.annotation is ValidatedRequestData

    def resolve(self,
                route: Route,
                data: http.RequestData):
        body_field = route.link.body_field
        if not body_field:
            return data
        validator = body_field.schema
        try:
            return validator.validate(data)
        except exceptions.ValidationError as exc:
            raise exceptions.BadRequest(dict(exc))


class PrimitiveParamComponent(Component):
    def can_handle_parameter(self, parameter: inspect.Parameter):
        return parameter.annotation in (
            str, int, float, bool, datetime.datetime, datetime.date,
            datetime.time, decimal.Decimal, parameter.empty
        )

    def resolve(self,
                parameter: inspect.Parameter,
                path_params: ValidatedPathParams,
                query_params: ValidatedQueryParams):
        if parameter.name in path_params:
            return path_params[parameter.name]
        return query_params[parameter.name]


class CompositeParamComponent(Component):
    def can_handle_parameter(self, parameter: inspect.Parameter):
        return (isinstance(parameter.annotation, type)
                and issubclass(parameter.annotation, schemas.Schema))

    def resolve(self,
                parameter: inspect.Parameter,
                data: ValidatedRequestData):
        return parameter.annotation(data)


VALIDATION_COMPONENTS = (
    RequestDataComponent(),
    ValidatePathParamsComponent(),
    ValidateQueryParamsComponent(),
    ValidateRequestDataComponent(),
    PrimitiveParamComponent(),
    CompositeParamComponent()
)
