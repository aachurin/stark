import os
import importlib
from importlib.util import find_spec


def get_path(package_path):
    if ':' in package_path:
        package, path = package_path.split(':', 1)
        package_dir = os.path.dirname(find_spec(package).origin)
        return os.path.join(package_dir, path)
    else:
        return package_path


def import_path(paths):
    if isinstance(paths, str):
        paths = [paths]
    for num, path in enumerate(paths, 1):
        try:
            module, attr = path.rsplit('.', 1)
            module = importlib.import_module(module)
            return getattr(module, attr)
        except ImportError:
            if num == len(paths):
                raise
