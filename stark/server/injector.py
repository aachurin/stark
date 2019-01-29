import asyncio
import inspect

from stark.exceptions import ConfigurationError
from stark.server.components import ReturnValue


class BaseInjector():
    def run(self, func, state):
        raise NotImplementedError()


class Injector(BaseInjector):
    allow_async = False

    def __init__(self, components, initial):
        self.instances = {}
        self.components = components
        self.initial = dict(initial)
        self.reverse_initial = {
            val: key for key, val in initial.items()
        }
        self.resolver_cache = {}

    def resolve_function(self,
                         func,
                         output_name=None,
                         seen_state=None,
                         parent_parameter=None,
                         set_return=False,
                         singleton=False):
        if seen_state is None:
            seen_state = set(self.initial)

        cache_steps = True
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

            # Check if the parameter class in 'singletons'
            if parameter.annotation in self.instances:
                instance = self.instances[parameter.annotation]
                consts[parameter.name] = instance
                continue

            # The 'Parameter' annotation can be used to get the parameter
            # itself. Used for example in 'Header' components that need the
            # parameter name in order to lookup a particular value.
            if parameter.annotation is inspect.Parameter:
                if singleton:
                    msg = 'Singleton component "%s" cannot depend on inspect.Parameter'
                    raise ConfigurationError(msg % self.__class__.__name__)
                consts[parameter.name] = parent_parameter
                continue

            # Otherwise, find a component to resolve the parameter.
            for component in self.components:
                if component.can_handle_parameter(parameter):
                    identity = component.identity(parameter)
                    kwargs[parameter.name] = identity
                    if identity not in seen_state:
                        seen_state.add(identity)
                        resolved_steps, can_cache = self.resolve_function(
                            func=component.resolve,
                            output_name=identity,
                            seen_state=seen_state,
                            parent_parameter=parameter,
                            singleton=component.is_singleton()
                        )
                        steps += resolved_steps
                        cache_steps = cache_steps and can_cache
                    break
            else:
                msg = 'No component able to handle parameter "%s" on function "%s".'
                raise ConfigurationError(msg % (parameter.name, func.__name__))

        is_async = asyncio.iscoroutinefunction(func)
        if is_async and not self.allow_async:
            msg = 'Function "%s" may not be async.'
            raise ConfigurationError(msg % (func.__name__, ))

        if singleton:
            orig_func = func
            cache_steps = False

            def func(**kw):
                ret = orig_func(**kw)
                self.instances[output_name] = ret
                return ret

        step = (func, is_async, kwargs, consts, output_name, set_return)
        steps.append(step)

        return steps, cache_steps

    def resolve_functions(self, funcs, state):
        steps = []
        seen_state = set(self.initial) | set(state)
        cache_steps_result = True
        for func in funcs:
            func_steps, cache_steps = self.resolve_function(func, seen_state=seen_state, set_return=True)
            steps.extend(func_steps)
            cache_steps_result = cache_steps_result and cache_steps
        return steps, cache_steps_result

    def run(self, funcs, state):
        funcs = tuple(funcs)
        try:
            steps = self.resolver_cache[funcs]
        except KeyError:
            if not funcs:
                return
            steps, cache_steps = self.resolve_functions(funcs, state)
            if cache_steps:
                self.resolver_cache[funcs] = steps

        output_name = None

        for func, is_async, kwargs, consts, output_name, set_return in steps:
            func_kwargs = {key: state[val] for key, val in kwargs.items()}
            func_kwargs.update(consts)
            state[output_name] = func(**func_kwargs)
            if set_return:
                state['return_value'] = state[output_name]

        return state[output_name]


class ASyncInjector(Injector):
    allow_async = True

    async def run_async(self, funcs, state):
        funcs = tuple(funcs)
        try:
            steps = self.resolver_cache[funcs]
        except KeyError:
            if not funcs:
                return
            steps, cache_steps = self.resolve_functions(funcs, state)
            if cache_steps:
                self.resolver_cache[funcs] = steps

        output_name = None

        for func, is_async, kwargs, consts, output_name, set_return in steps:
            func_kwargs = {key: state[val] for key, val in kwargs.items()}
            func_kwargs.update(consts)
            if is_async:
                state[output_name] = await func(**func_kwargs)
            else:
                state[output_name] = func(**func_kwargs)
            if set_return:
                state['return_value'] = state[output_name]

        return state[output_name]
