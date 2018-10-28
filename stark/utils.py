import os
import typing
from importlib.util import find_spec
from collections import OrderedDict


def get_path(dirs):
    if not isinstance(dirs, (list, tuple)):
        dirs = (dirs,)
    result = []
    for item in dirs:
        if ':' in item:
            package, path = item.split(':', 1)
            package_dir = os.path.dirname(find_spec(package).origin)
            result.append(os.path.join(package_dir, path))
        else:
            result.append(item)
    return result


def get_vdirs(vdirs: typing.Union[str, list, tuple, dict]):
    result = OrderedDict()
    if isinstance(vdirs, dict):
        for k, v in vdirs.items():
            result[k] = get_path(v)
        return result
    if isinstance(vdirs, (list, tuple)):
        for item in vdirs:
            for k, v in get_vdirs(item).items():
                result.setdefault(k, []).extend(v)
        return result
    result.setdefault('', []).extend(get_path(vdirs))
    return result
