import inspect
import typing
from stark.server.core import Route
from stark.server.utils import import_path


__all__ = ('resource_routes', 'CreateRoute', 'ListRoute', 'UpdateRoute',
           'GetRoute', 'DeleteRoute', 'ActionRoute')


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
        tags=[resource, '#create']
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
        tags=[resource, '#list']
    )


def make_get_route(resource: str,
                   handler: typing.Union[str, typing.Callable],
                   lookup_param: str,
                   baseurl: str = None,
                   documented: bool = True,
                   standalone: bool = False):
    if baseurl is None:
        baseurl = resource
    check_object_lookup_parameter(lookup_param, handler)
    url = "/" + ("%s/{%s}" % (baseurl, lookup_param)).lstrip("/")
    return Route(
        url=url,
        method="GET",
        handler=find_handler(handler),
        documented=documented,
        standalone=standalone,
        tags=[resource, '#get']
    )


def make_update_route(resource: str,
                      handler: typing.Union[str, typing.Callable],
                      lookup_param: str,
                      baseurl: str = None,
                      documented: bool = True,
                      standalone: bool = False):
    check_object_lookup_parameter(lookup_param, handler)
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


def make_delete_route(resource: str,
                      handler: typing.Union[str, typing.Callable],
                      lookup_param: str,
                      baseurl: str = None,
                      documented: bool = True,
                      standalone: bool = False):
    check_object_lookup_parameter(lookup_param, handler)
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
    if lookup_param:
        check_object_lookup_parameter(lookup_param, handler)
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


def resource_routes(
        resource: str,
        baseurl: str = None,
        lookup_param: str = None,
        documented: bool = True,
        create_handler: typing.Union[str, typing.Callable] = None,
        update_handler: typing.Union[str, typing.Callable] = None,
        get_handler: typing.Union[str, typing.Callable] = None,
        list_handler: typing.Union[str, typing.Callable] = None,
        delete_handler: typing.Union[str, typing.Callable] = None
):
    routes = []
    if create_handler:
        routes += [
            make_create_route(
                resource,
                create_handler,
                baseurl=baseurl,
                documented=documented
            )
        ]
    if list_handler:
        routes += [
            make_list_route(
                resource,
                list_handler,
                baseurl=baseurl,
                documented=documented
            )
        ]
    if get_handler:
        routes += [
            make_get_route(
                resource,
                get_handler,
                baseurl=baseurl,
                lookup_param=lookup_param,
                documented=documented
            )
        ]
    if update_handler:
        routes += [
            make_update_route(
                resource,
                update_handler,
                baseurl=baseurl,
                lookup_param=lookup_param,
                documented=documented
            )
        ]
    if delete_handler:
        routes += [
            make_delete_route(
                resource,
                delete_handler,
                baseurl=baseurl,
                lookup_param=lookup_param,
                documented=documented
            )
        ]
    return routes


def find_handler(handler: typing.Union[str, typing.Callable]) -> typing.Callable:
    if isinstance(handler, str):
        handler = import_path(handler)
    assert callable(handler)
    return handler


def check_object_lookup_parameter(lookup_param, handler: typing.Union[str, typing.Callable]):
    assert lookup_param is not None, (
        "Resource() missing required `lookup_param`"
    )
    handler = find_handler(handler)
    params = [x for x in inspect.signature(handler).parameters.keys()]
    assert lookup_param in params, (
        f"Handler `{handler.__name__}` missing required parameter `{lookup_param}`."
    )


CreateRoute = make_create_route
ListRoute = make_list_route
UpdateRoute = make_update_route
GetRoute = make_get_route
DeleteRoute = make_delete_route
ActionRoute = make_action_route
