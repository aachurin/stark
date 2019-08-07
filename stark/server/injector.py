import asyncio
import inspect
from stark import exceptions
from stark.server.components import ReturnValue, Parameter


class BaseInjector:
    def run(self, func, state, cache=True):
        raise RuntimeError("Not supported")

    async def run_async(self, funcs, state, cache=True):
        raise RuntimeError("Not supported")


class Injector(BaseInjector):
    allow_async = False

    def __init__(self, components, initial):
        self.components = components
        self.initial = dict(initial)
        self.reverse_initial = {
            val: key for key, val in initial.items()
        }
        self.singletons = {}
        self.resolver_cache = {}

    def resolve_validation_parameters(self,
                                      func):
        unique = {}
        for holder, param in self._resolve_validation_parameters(func, set()):
            if param.name in unique:
                cur_holder, cur_param = unique[param.name]
                if cur_param != param:
                    msg = "\nConflicting parameters:\n%s( .. %s ..)\nand\n%s ( .. %s ..)"
                    raise exceptions.ConfigurationError(msg % (cur_holder, cur_param, holder, param))
                elif not cur_param.description and param.description:
                    unique[param.name] = (holder, param)
            else:
                unique[param.name] = (holder, param)
        return {k: v[1] for k, v in unique.items()}

    def _resolve_validation_parameters(self,
                                       func,
                                       seen_state):
        parameters = []
        signature = inspect.signature(func)
        for parameter in signature.parameters.values():
            if (parameter.annotation in (ReturnValue, inspect.Parameter)
                    or parameter.annotation in self.reverse_initial):
                continue
            for component in self.components:
                if component.can_handle_parameter(parameter):
                    identity = component.identity(parameter)
                    if identity not in seen_state:
                        seen_state.add(identity)
                        params = component.get_validation_parameters(func, parameter)
                        parameters += [(func, Parameter.from_obj(p)) for p in params]
                        parameters += self._resolve_validation_parameters(component.resolve, seen_state)
                    break
            else:
                msg = 'No component able to handle parameter "%s" on function "%s".'
                raise exceptions.ConfigurationError(msg % (parameter.name, func.__qualname__))
        return parameters

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
            if inspect.isclass(func):
                return_annotation = func
            else:
                return_annotation = signature.return_annotation
            if return_annotation in self.reverse_initial:
                # some functions can override initial state
                output_name = self.reverse_initial[return_annotation]
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
