from stark import App, http
from stark.codecs import OpenAPICodec
from stark.server.asgi import ASGIReceive, ASGIScope, ASGISend
from stark.server.wsgi import WSGIEnviron, WSGIStartResponse


def serve_schema(app: App):
    codec = OpenAPICodec()
    content = codec.encode(app.document)
    headers = {'Content-Type': 'application/vnd.oai.openapi'}
    return http.Response(content, headers=headers)


def serve_documentation(app: App):
    template_name = 'apistar/index.html'
    code_style = default_code_style
    return app.render_template(
        template_name,
        document=app.document,
        langs=['python', 'javascript'],
        code_style=code_style
    )


def serve_static_wsgi(app: App, environ: WSGIEnviron, start_response: WSGIStartResponse):
    return app.statics(environ, start_response)


async def serve_static_asgi(app: App, scope: ASGIScope, receive: ASGIReceive, send: ASGISend):
    instance = app.statics(scope)
    await instance(receive, send)


default_code_style = """
.highlight.python .word{color:#d372e3;}
.highlight.python .string{color:#8bc76c;}
.highlight.python .attr{color:#42b0f5;}
.highlight.python .kwarg{color:#db985c;}
.highlight.python .global{color:#1fb8c4;}
"""
