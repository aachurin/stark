import inspect
import typing
from stark import exceptions


class Parameter(typing.NamedTuple):
    name: str
    annotation: typing.Type
    description: str = ""
    default: typing.Any = inspect.Signature.empty
    empty = inspect.Signature.empty

    def __eq__(self, other):
        return type(self) == type(other) and self[:3] == other[:3]

    def __repr__(self):
        r = "%s: %r" % (self.name, self.annotation)
        if self.default is not self.empty:
            r += " = " + repr(self.default)
        return r

    @classmethod
    def from_obj(cls, other):
        if isinstance(other, inspect.Parameter):
            return cls.from_inspect(other)
        if isinstance(other, Parameter):
            return other
        assert isinstance(other, tuple)
        return cls(*other)

    @classmethod
    def from_inspect(cls, parameter, description=""):
        assert isinstance(parameter, inspect.Parameter)
        return cls(parameter.name,
                   parameter.annotation,
                   default=parameter.default,
                   description=description
                   )


class Component:
    singleton = False

    def __init_subclass__(cls, **kwargs):
        if cls.singleton:
            if cls.can_handle_parameter is not Component.can_handle_parameter:
                msg = (
                    'Component "%s" should not override `can_handle_parameter`, '
                    'since it is a singleton'
                )
                raise exceptions.ConfigurationError(msg % cls.__name__)

    def identity(self, parameter: inspect.Parameter):
        """
        Each component needs a unique identifier string that we use for lookups
        from the `state` dictionary when we run the dependency injection.
        """
        parameter_name = parameter.name.lower()
        annotation_name = parameter.annotation.__name__.lower()

        # If `resolve_parameter` includes `Parameter` then we use an identifier
        # that is additionally parameterized by the parameter name.
        args = inspect.signature(self.resolve).parameters.values()
        if inspect.Parameter in [arg.annotation for arg in args]:
            return annotation_name + ':' + parameter_name

        # Standard case is to use the class name, lowercased.
        return annotation_name

    def can_handle_parameter(self, parameter: inspect.Parameter):
        # Return `True` if this component can handle the given parameter.
        #
        # The default behavior is for components to handle whatever class
        # is used as the return annotation by the `resolve` method.
        #
        # You can override this for more customized styles, for example if you
        # wanted name-based parameter resolution, or if you want to provide
        # a value for a range of different types.
        #
        # Eg. Include the `Request` instance for any parameter named `request`.
        if inspect.isclass(self.resolve):
            return_annotation = self.resolve
        else:
            return_annotation = inspect.signature(self.resolve).return_annotation
        if return_annotation is inspect.Signature.empty:
            msg = (
                      'Component "%s" must include a return annotation on the '
                      '`resolve()` method, or override `can_handle_parameter`.'
                  ) % self.__class__.__name__
            raise exceptions.ConfigurationError(msg)
        return parameter.annotation is return_annotation

    def get_validation_parameters(
            self,
            func,
            parameter: inspect.Parameter
    ) -> typing.List[typing.Union[Parameter, inspect.Parameter]]:
        return []

    @typing.no_type_check
    def resolve(self):
        raise NotImplementedError()


ReturnValue = typing.TypeVar('ReturnValue')


def component_from_class(cls: type) -> Component:
    new_component = Component()
    new_component.resolve = cls
    return new_component
