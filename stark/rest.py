import typing
from stark.server.core import Route
from stark.server.utils import import_path


__all__ = ("Router", )


def make_create_route(resource: str,
                      handler: typing.Union[str, typing.Callable],
                      baseurl: str = None,
                      documented: bool = True,
                      standalone: bool = False):
    if baseurl is None:
        baseurl = resource
    url = "/" + baseurl.lstrip("/")
    return Route(
        url=url,
        method="POST",
        handler=find_handler(handler),
        documented=documented,
        standalone=standalone,
        tags=[resource, "#create"]
    )


def make_list_route(resource: str,
                    handler: typing.Union[str, typing.Callable],
                    baseurl: str = None,
                    documented: bool = True,
                    standalone: bool = False):
    if baseurl is None:
        baseurl = resource
    url = "/" + baseurl.lstrip("/")
    return Route(
        url=url,
        method="GET",
        handler=find_handler(handler),
        documented=documented,
        standalone=standalone,
        tags=[resource, "#list"]
    )


def make_retrieve_route(resource: str,
                        handler: typing.Union[str, typing.Callable],
                        lookup_param: str,
                        baseurl: str = None,
                        documented: bool = True,
                        standalone: bool = False):
    if baseurl is None:
        baseurl = resource
    url = "/" + ("%s/{%s}" % (baseurl, lookup_param)).lstrip("/")
    return Route(
        url=url,
        method="GET",
        handler=find_handler(handler),
        documented=documented,
        standalone=standalone,
        tags=[resource, "#get"]
    )


def make_update_route(resource: str,
                      handler: typing.Union[str, typing.Callable],
                      lookup_param: str,
                      baseurl: str = None,
                      documented: bool = True,
                      standalone: bool = False):
    if baseurl is None:
        baseurl = resource
    url = "/" + ("%s/{%s}" % (baseurl, lookup_param)).lstrip("/")
    return Route(
        url=url,
        method="PUT",
        handler=find_handler(handler),
        documented=documented,
        standalone=standalone,
        tags=[resource, "#update"]
    )


def make_destroy_route(resource: str,
                       handler: typing.Union[str, typing.Callable],
                       lookup_param: str,
                       baseurl: str = None,
                       documented: bool = True,
                       standalone: bool = False):
    if baseurl is None:
        baseurl = resource
    url = "/" + ("%s/{%s}" % (baseurl, lookup_param)).lstrip("/")
    return Route(
        url=url,
        method="DELETE",
        handler=find_handler(handler),
        documented=documented,
        standalone=standalone,
        tags=[resource, "#delete"]
    )


def make_action_route(resource: str,
                      handler: typing.Union[str, typing.Callable],
                      method: str,
                      action: str = None,
                      lookup_param: str = None,
                      baseurl: str = None,
                      documented: bool = True,
                      standalone: bool = False):
    if baseurl is None:
        baseurl = resource
    handler = find_handler(handler)
    if action is None:
        action = handler.__name__
    if lookup_param:
        url = "/" + ("%s/{%s}/%s" % (baseurl, lookup_param, action)).lstrip("/")
    else:
        url = "/" + ("%s/%s" % (baseurl, action)).lstrip("/")
    return Route(
        url=url,
        method=method,
        handler=handler,
        documented=documented,
        standalone=standalone,
        tags=[resource, "#action"]
    )


def find_handler(handler: typing.Union[str, typing.Callable]) -> typing.Callable:
    if isinstance(handler, str):
        handler = import_path(handler)
    assert callable(handler)
    return handler


class Router:
    def __init__(
            self,
            resource: str,
            baseurl: str = None,
            lookup_param: str = None,
            documented: bool = True
    ):
        self.resource = resource
        self.baseurl = baseurl
        self.lookup_param = lookup_param
        self.documented = documented

    def create_route(self, handler: typing.Union[str, typing.Callable]):
        return make_create_route(
            self.resource,
            handler,
            self.baseurl,
            self.documented
        )

    def list_route(self, handler: typing.Union[str, typing.Callable]):
        return make_list_route(
            self.resource,
            handler,
            self.baseurl,
            self.documented
        )

    def retrieve_route(self, handler: typing.Union[str, typing.Callable]):
        return make_retrieve_route(
            self.resource,
            handler,
            self.lookup_param,
            self.baseurl,
            self.documented
        )

    def update_route(self, handler: typing.Union[str, typing.Callable]):
        return make_update_route(
            self.resource,
            handler,
            self.lookup_param,
            self.baseurl,
            self.documented
        )

    def destroy_route(self, handler: typing.Union[str, typing.Callable]):
        return make_destroy_route(
            self.resource,
            handler,
            self.lookup_param,
            self.baseurl,
            self.documented
        )

    def action_route(
            self,
            handler: typing.Union[str, typing.Callable],
            method: str,
            action: str = None,
            detail: bool = True
    ):
        return make_action_route(
            self.resource,
            handler,
            method,
            action,
            self.lookup_param if detail else None,
            self.baseurl,
            self.documented
        )
