import asyncio
import inspect
from stark import exceptions
from stark.server.components import ReturnValue


class BaseInjector:
    def run(self, func, state, cache=True):
        raise RuntimeError("Not supported")

    async def run_async(self, funcs, state, cache=True):
        raise RuntimeError("Not supported")


class Injector(BaseInjector):
    allow_async = False

    def __init__(self, components, initial):
        self.components = [self.ensure_component(comp) for comp in components]
        self.initial = dict(initial)
        self.reverse_initial = {
            val: key for key, val in initial.items()
        }
        self.singletons = {}
        self.resolver_cache = {}

    @staticmethod
    def ensure_component(comp):
        msg = 'Component "%s" must implement `identity` method.'
        assert hasattr(comp, 'identity') and callable(comp.identity),\
            msg % comp.__class__.__name__
        msg = 'Component "%s" must implement `can_handle_parameter` method.'
        assert hasattr(comp, 'can_handle_parameter') and callable(comp.can_handle_parameter),\
            msg % comp.__class__.__name__
        msg = 'Component "%s" must implement `resolve` method.'
        assert hasattr(comp, 'resolve') and callable(comp.resolve),\
            msg % comp.__class__.__name__
        return comp

    def resolve_function(self,
                         func,
                         seen_state,
                         output_name=None,
                         parent_parameter=None,
                         set_return=False):

        steps = []
        kwargs = {}
        consts = {}

        signature = inspect.signature(func)

        if output_name is None:
            if signature.return_annotation in self.reverse_initial:
                # some functions can override initial state
                output_name = self.reverse_initial[signature.return_annotation]
            else:
                output_name = 'return_value'

        for parameter in signature.parameters.values():
            if parameter.annotation is ReturnValue:
                kwargs[parameter.name] = 'return_value'
                continue

            # Check if the parameter class exists in 'initial'.
            if parameter.annotation in self.reverse_initial:
                initial_kwarg = self.reverse_initial[parameter.annotation]
                kwargs[parameter.name] = initial_kwarg
                continue

            # The 'Parameter' annotation can be used to get the parameter
            # itself. Used for example in 'Header' components that need the
            # parameter name in order to lookup a particular value.
            if parameter.annotation is inspect.Parameter:
                consts[parameter.name] = parent_parameter
                continue

            # Otherwise, find a component to resolve the parameter.
            for component in self.components:
                if component.can_handle_parameter(parameter):
                    if component in self.singletons:
                        consts[parameter.name] = self.singletons[component]
                    else:
                        identity = component.identity(parameter)
                        kwargs[parameter.name] = identity
                        if identity not in seen_state:
                            seen_state.add(identity)
                            resolved_steps = self.resolve_function(
                                component.resolve,
                                seen_state,
                                output_name=identity,
                                parent_parameter=parameter
                            )
                            steps += resolved_steps
                            if getattr(component, 'singleton', False):
                                steps.append(self.resolve_singleton(component, identity))
                    break
            else:
                msg = 'No component able to handle parameter "%s" on function "%s".'
                raise exceptions.ConfigurationError(msg % (parameter.name, func.__qualname__))

        is_async = asyncio.iscoroutinefunction(func)
        if is_async and not self.allow_async:
            msg = 'Function "%s" may not be async.'
            raise exceptions.ConfigurationError(msg % (func.__qualname__, ))

        step = (func, is_async, kwargs, consts, output_name, set_return)
        steps.append(step)

        return steps

    def resolve_singleton(self, component, identity):
        kwargs = {'value': identity}

        def func(value):
            self.singletons[component] = value

        return func, False, kwargs, (), '$nocache', False

    def resolve_functions(self, funcs, state):
        steps = []
        seen_state = set(self.initial) | set(state)
        for func in funcs:
            func_steps = self.resolve_function(func, seen_state, set_return=True)
            steps.extend(func_steps)
        return steps

    def run(self, funcs, state, cache=True):
        if not funcs:
            return
        funcs = tuple(funcs)
        try:
            steps = self.resolver_cache[funcs]
        except KeyError:
            steps = self.resolve_functions(funcs, state)
            if cache:
                self.resolver_cache[funcs] = steps

        for func, is_async, kwargs, consts, output_name, set_return in steps:
            func_kwargs = {key: state[val] for key, val in kwargs.items()}
            func_kwargs.update(consts)
            state[output_name] = func(**func_kwargs)
            if set_return:
                state['return_value'] = state[output_name]

        if '$nocache' in state:
            self.resolver_cache.pop(funcs)

        # noinspection PyUnboundLocalVariable
        return state[output_name]


class ASyncInjector(Injector):
    allow_async = True

    async def run_async(self, funcs, state, cache=True):
        if not funcs:
            return
        funcs = tuple(funcs)
        try:
            steps = self.resolver_cache[funcs]
        except KeyError:
            steps = self.resolve_functions(funcs, state)
            if cache:
                self.resolver_cache[funcs] = steps

        for func, is_async, kwargs, consts, output_name, set_return in steps:
            func_kwargs = {key: state[val] for key, val in kwargs.items()}
            func_kwargs.update(consts)
            if is_async:
                state[output_name] = await func(**func_kwargs)
            else:
                state[output_name] = func(**func_kwargs)
            if set_return:
                state['return_value'] = state[output_name]

        if cache and '$nocache' in state:
            self.resolver_cache.pop(funcs)

        # noinspection PyUnboundLocalVariable
        return state[output_name]
