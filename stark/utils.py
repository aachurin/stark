import os
from importlib.util import find_spec


def get_path(package_path):
    if ':' in package_path:
        package, path = package_path.split(':', 1)
        package_dir = os.path.dirname(find_spec(package).origin)
        return os.path.join(package_dir, path)
    else:
        return package_path
