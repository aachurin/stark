from http import HTTPStatus

from stark import exceptions
from stark.compat import aiofiles, whitenoise
from stark.server.utils import get_path


class BaseStaticFiles():

    def __call__(self, environ, start_response):
        raise NotImplementedError()


class StaticFiles(BaseStaticFiles):
    """
    Static file handling for WSGI applications, using `whitenoise`.
    """
    def __init__(self, prefix: str, static_dirs: str = None):
        self.check_requirements()
        self.whitenoise = whitenoise.WhiteNoise(application=self.not_found)

        if not isinstance(static_dirs, (list, tuple)):
            static_dirs = [static_dirs]

        for static_dir in static_dirs:
            if isinstance(static_dir, dict):
                for files_prefix, path in static_dir.items():
                    path = get_path(path)
                    self.whitenoise.add_files(path, prefix=(prefix + '/' + files_prefix).rstrip('/'))
            else:
                path = get_path(static_dir)
                self.whitenoise.add_files(path, prefix=prefix)

    def check_requirements(self):
        if whitenoise is None:
            raise RuntimeError('`whitenoise` must be installed to use `StaticFiles`.')

    def __call__(self, environ, start_response):
        return self.whitenoise(environ, start_response)

    def not_found(self, environ, start_response):
        raise exceptions.NotFound()


class ASyncStaticFiles(StaticFiles):
    """
    Static file handling for ASGI applications, using `whitenoise` and `aiofiles`.
    """
    def check_requirements(self):
        if whitenoise is None:
            raise RuntimeError('`whitenoise` must be installed to use `ASyncStaticFiles`.')
        if aiofiles is None:
            raise RuntimeError('`aiofiles` must be installed to use `ASyncStaticFiles`.')

    def __call__(self, scope):
        path = scope['path'].encode('iso-8859-1', 'replace').decode('utf-8', 'replace')
        if self.whitenoise.autorefresh:
            static_file = self.whitenoise.find_file(path)
        else:
            static_file = self.whitenoise.files.get(path)
        if static_file is None:
            # noinspection PyUnusedLocal
            async def not_found(receive, send):
                raise exceptions.NotFound()
            return not_found
        else:
            return ASGIFileSession(static_file, scope)


class ASGIFileSession():
    def __init__(self, static_file, scope):
        self.static_file = static_file
        self.scope = scope
        self.headers = {}
        for key, value in scope['headers']:
            wsgi_key = 'HTTP_' + key.decode().upper().replace('-', '_')
            wsgi_value = value.decode()
            self.headers[wsgi_key] = wsgi_value

    async def __call__(self, receive, send):
        status, headers, file = await self.get_response(self.scope['method'], self.headers)
        await send({
            'type': 'http.response.start',
            'status': status.value,
            'headers': [
                (key.lower().encode(), value.encode())
                for key, value in headers
            ]
        })
        if file is None:
            await send({
                'type': 'http.response.body',
                'body': b''
            })
        else:
            try:
                chunk = await file.read(8192)
                more_body = True

                while more_body:
                    next_chunk = await file.read(8192)
                    more_body = bool(next_chunk)

                    await send({
                        'type': 'http.response.body',
                        'body': chunk,
                        'more_body': more_body
                    })
                    chunk = next_chunk
            finally:
                # Free resource
                await file.close()

    async def get_response(self, method, request_headers):
        if method != 'GET' and method != 'HEAD':
            return (
                HTTPStatus.METHOD_NOT_ALLOWED,
                (('Allow', 'GET, HEAD'),),
                None
            )
        elif self.static_file.file_not_modified(request_headers):
            return self.static_file.not_modified_response
        path, headers = self.static_file.get_path_and_headers(request_headers)
        if method != 'HEAD':
            file_handle = await aiofiles.open(path, 'rb')
        else:
            file_handle = None
        return (HTTPStatus.OK, headers, file_handle)
