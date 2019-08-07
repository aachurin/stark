import sys
import importlib
import werkzeug
from stark import exceptions
from stark.http import HTMLResponse, JSONResponse, PathParams, Response
from stark.server.adapters import ASGItoWSGIAdapter
from stark.server.asgi import ASGI_COMPONENTS, ASGIReceive, ASGIScope, ASGISend
from stark.server.components import Component, ReturnValue
from stark.server.core import Route, Settings, generate_document
from stark.server.injector import ASyncInjector, Injector, BaseInjector
from stark.server.router import Router
from stark.server.staticfiles import ASyncStaticFiles, StaticFiles
from stark.server.templates import Templates
from stark.server.validation import VALIDATION_COMPONENTS
from stark.server.wsgi import RESPONSE_STATUS_TEXT, WSGI_COMPONENTS, WSGIEnviron, WSGIStartResponse
from stark.server.utils import import_path
from stark.document import Document


class App:
    interface = "wsgi"

    injector: BaseInjector
    document: Document
    router: Router
    templates: Templates
    statics: StaticFiles

    def __init__(self, settings_module: str = 'settings', event_hooks=None):
        mod = importlib.import_module(settings_module)
        self.settings = Settings(mod)

        static_url = self.settings.STATIC_URL
        template_dirs = list(self.settings.TEMPLATE_DIRS)
        static_dirs = list(self.settings.STATIC_DIRS)
        schema_url = self.settings.SCHEMA_URL
        docs_url = self.settings.DOCS_URL
        docs_theme = self.settings.DOCS_THEME
        components = self.settings.COMPONENTS
        routes = self.settings.ROUTES

        if docs_url:
            template_dirs += [
                "stark:templates",
                {"apistar": f"stark:themes/{docs_theme}/templates"}
            ]
            static_dirs += [f"stark:themes/{docs_theme}/static"]

        if not static_dirs:
            static_url = None

        if event_hooks:
            msg = "event_hooks must be a list."
            assert isinstance(event_hooks, list), msg

        self.debug = getattr(self.settings, "DEBUG", False)
        self.init_injector(components)
        self.init_templates(template_dirs)
        self.init_staticfiles(static_url, static_dirs)
        self.event_hooks = event_hooks

        module = importlib.import_module(routes)
        routes = module.routes or []
        routes += self.include_extra_routes(schema_url, docs_url, static_url)

        self.init_router(routes)
        self.init_document(routes)

        # Ensure event hooks can all be instantiated.
        self.get_event_hooks()

    def include_extra_routes(self, schema_url=None, docs_url=None, static_url=None):
        extra_routes = []

        from stark.server.handlers import serve_documentation, serve_schema, serve_static_wsgi

        if schema_url:
            extra_routes += [
                Route(schema_url, method='GET', handler=serve_schema, documented=False)
            ]
        if docs_url:
            extra_routes += [
                Route(docs_url, method='GET', handler=serve_documentation, documented=False)
            ]
        if static_url:
            static_url = static_url.rstrip('/') + '/{+filename}'
            extra_routes += [
                Route(
                    static_url, method='GET', handler=serve_static_wsgi,
                    name='static', documented=False, standalone=True
                )
            ]
        return extra_routes

    def init_document(self, routes):
        self.document = generate_document(routes)

    def init_router(self, routes):
        for route in routes:
            route.setup(self.injector)
        self.router = Router(routes)

    def init_templates(self, template_dirs):
        if not template_dirs:
            self.templates = None
        else:
            template_globals = {
                'reverse_url': self.reverse_url,
                'static_url': self.static_url
            }
            self.templates = Templates(template_dirs, template_globals)

    def init_staticfiles(self, static_url, static_dirs):
        if not static_dirs:
            self.statics = None
        else:
            self.statics = StaticFiles(static_url, static_dirs)

    def init_injector(self, components=None):
        app_components = list(WSGI_COMPONENTS + VALIDATION_COMPONENTS)
        for comp in (components or []):
            if isinstance(comp, str):
                comp = import_path(comp, ["components", "COMPONENTS"])
            if isinstance(comp, Component):
                app_components.append(comp)
            elif isinstance(comp, (list, tuple)):
                for c in comp:
                    if not isinstance(c, Component):
                        msg = "Could not load component %r"
                        raise exceptions.ConfigurationError(msg % c)
                app_components += list(comp)
            else:
                msg = "Could not load component %r"
                raise exceptions.ConfigurationError(msg % comp)
        initial_components = {
            'environ': WSGIEnviron,
            'start_response': WSGIStartResponse,
            'exc': Exception,
            'app': App,
            'path_params': PathParams,
            'route': Route,
            'response': Response,
            'settings': Settings
        }
        self.injector = Injector(app_components, initial_components)

    def get_event_hooks(self):
        event_hooks = []
        for hook in self.event_hooks or []:
            if isinstance(hook, type):
                # New style usage, instantiate hooks on requests.
                event_hooks.append(hook())
            else:
                # Old style usage, to be deprecated on the next version bump.
                event_hooks.append(hook)

        on_request = [
            hook.on_request for hook in event_hooks
            if hasattr(hook, 'on_request')
        ]

        on_response = [
            hook.on_response for hook in reversed(event_hooks)
            if hasattr(hook, 'on_response')
        ]

        on_error = [
            hook.on_error for hook in reversed(event_hooks)
            if hasattr(hook, 'on_error')
        ]

        return on_request, on_response, on_error

    def static_url(self, filename):
        assert self.router is not None, "Router is not initialized"
        return self.router.reverse_url('static', filename=filename)

    def reverse_url(self, name: str, **params):
        assert self.router is not None, "Router is not initialized"
        return self.router.reverse_url(name, **params)

    def render_template(self, path: str, **context):
        return self.templates.render_template(path, **context)

    def serve(self, host, port, debug=False, **options):
        self.debug = debug
        if 'use_debugger' not in options:
            options['use_debugger'] = debug
        if 'use_reloader' not in options:
            options['use_reloader'] = debug
        werkzeug.run_simple(host, port, self, **options)

    @staticmethod
    def render_response(return_value: ReturnValue) -> Response:
        if return_value is None:
            return Response("No Content", 204)
        if isinstance(return_value, Response):
            return return_value
        elif isinstance(return_value, str):
            return HTMLResponse(return_value)
        return JSONResponse(return_value)

    @staticmethod
    def exception_handler(exc: Exception) -> Response:
        if isinstance(exc, exceptions.HTTPException):
            return JSONResponse(exc.detail, exc.status_code, exc.get_headers())
        raise exc

    @staticmethod
    def error_handler() -> Response:
        return JSONResponse('Server error', 500, exc_info=sys.exc_info())

    def finalize_wsgi(self, response: Response, start_response: WSGIStartResponse):
        if self.debug and response.exc_info is not None:
            exc_info = response.exc_info
            raise exc_info[0].with_traceback(exc_info[1], exc_info[2])

        start_response(
            RESPONSE_STATUS_TEXT[response.status_code],
            list(response.headers),
            response.exc_info
        )
        return [response.content]

    def __call__(self, environ, start_response):
        state = {
            'environ': environ,
            'start_response': start_response,
            'settings': self.settings,
            'exc': None,
            'app': self,
            'path_params': None,
            'route': None,
            'response': None,
        }
        method = environ['REQUEST_METHOD'].upper()
        path = environ['PATH_INFO']

        if self.event_hooks is None:
            on_request, on_response, on_error = [], [], []
        else:
            on_request, on_response, on_error = self.get_event_hooks()

        try:
            route, path_params = self.router.lookup(path, method)
            state['route'] = route
            state['path_params'] = path_params
            if route.standalone:
                funcs = [route.handler]
            else:
                funcs = (
                        on_request +
                        [route.handler, self.render_response] +
                        on_response +
                        [self.finalize_wsgi]
                )
            return self.injector.run(funcs, state)
        except Exception as exc:
            try:
                state['exc'] = exc
                # noinspection PyTypeChecker
                funcs = (
                        [self.exception_handler] +
                        on_response +
                        [self.finalize_wsgi]
                )
                return self.injector.run(funcs, state)
            except Exception as inner_exc:
                try:
                    state['exc'] = inner_exc
                    self.injector.run(on_error, state)
                finally:
                    funcs = [self.error_handler, self.finalize_wsgi]
                    return self.injector.run(funcs, state)


class ASyncApp(App):
    interface = "asgi"

    def include_extra_routes(self, schema_url=None, docs_url=None, static_url=None):
        extra_routes = []

        from stark.server.handlers import serve_documentation, serve_schema, serve_static_asgi

        if schema_url:
            extra_routes += [
                Route(schema_url, method='GET', handler=serve_schema, documented=False)
            ]
        if docs_url:
            extra_routes += [
                Route(docs_url, method='GET', handler=serve_documentation, documented=False)
            ]
        if static_url:
            static_url = static_url.rstrip('/') + '/{+filename}'
            extra_routes += [
                Route(
                    static_url, method='GET', handler=serve_static_asgi,
                    name='static', documented=False, standalone=True
                )
            ]
        return extra_routes

    def init_injector(self, components=None):
        components = components if components else []
        components = list(ASGI_COMPONENTS + VALIDATION_COMPONENTS) + components
        initial_components = {
            'scope': ASGIScope,
            'receive': ASGIReceive,
            'send': ASGISend,
            'exc': Exception,
            'app': App,
            'path_params': PathParams,
            'route': Route,
            'response': Response,
            'settings': Settings
        }
        self.injector = ASyncInjector(components, initial_components)

    def init_staticfiles(self, static_url, static_dirs):
        if not static_dirs:
            self.statics = None
        else:
            self.statics = ASyncStaticFiles(static_url, static_dirs)

    def __call__(self, scope):
        async def asgi_callable(receive, send):
            state = {
                'scope': scope,
                'receive': receive,
                'send': send,
                'exc': None,
                'app': self,
                'path_params': None,
                'route': None
            }
            method = scope['method']
            path = scope['path']

            if self.event_hooks is None:
                on_request, on_response, on_error = [], [], []
            else:
                on_request, on_response, on_error = self.get_event_hooks()

            try:
                route, path_params = self.router.lookup(path, method)
                state['route'] = route
                state['path_params'] = path_params
                if route.standalone:
                    funcs = [route.handler]
                else:
                    funcs = (
                            on_request +
                            [route.handler, self.render_response] +
                            on_response +
                            [self.finalize_asgi]
                    )
                await self.injector.run_async(funcs, state)
            except Exception as exc:
                try:
                    state['exc'] = exc
                    # noinspection PyTypeChecker
                    funcs = (
                            [self.exception_handler] +
                            on_response +
                            [self.finalize_asgi]
                    )
                    await self.injector.run_async(funcs, state)
                except Exception as inner_exc:
                    try:
                        state['exc'] = inner_exc
                        await self.injector.run_async(on_error, state)
                    finally:
                        funcs = [self.error_handler, self.finalize_asgi]
                        await self.injector.run_async(funcs, state)

        return asgi_callable

    async def finalize_asgi(self, response: Response, send: ASGISend, scope: ASGIScope):
        if response.exc_info is not None:
            if self.debug or scope.get('raise_exceptions', False):
                exc_info = response.exc_info
                raise exc_info[0].with_traceback(exc_info[1], exc_info[2])

        await send({
            'type': 'http.response.start',
            'status': response.status_code,
            'headers': [
                [key.encode(), value.encode()]
                for key, value in response.headers
            ]
        })
        await send({
            'type': 'http.response.body',
            'body': response.content
        })

    def serve(self, host, port, debug=False, **options):
        self.debug = debug
        if 'use_debugger' not in options:
            options['use_debugger'] = debug
        if 'use_reloader' not in options:
            options['use_reloader'] = debug
        wsgi = ASGItoWSGIAdapter(self, raise_exceptions=debug)
        werkzeug.run_simple(host, port, wsgi, **options)
