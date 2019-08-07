import os
import re
import sys
import typing
import importlib
from importlib.util import find_spec


def get_path(package_path):
    if ':' in package_path:
        package, path = package_path.split(':', 1)
        package_dir = os.path.dirname(find_spec(package).origin)
        return os.path.join(package_dir, path)
    else:
        return package_path


def import_path(path, alternatives=None):
    spec = importlib.util.find_spec(path)
    if spec is None:
        path, attr = path.rsplit('.', 1)
        attrs = [attr]
        if alternatives:
            attrs += alternatives
    else:
        attrs = alternatives or []
    module = importlib.import_module(path)
    for num, attr in enumerate(attrs, 1):
        try:
            return getattr(module, attr)
        except AttributeError:
            pass
    raise ImportError(
        "Could not load any of %s" % (", ".join([repr(path + "." + x) for x in attrs]))
    )


PARAM_OR_RETURNS_REGEX = re.compile(r":(?:param|returns)")
PARAM_REGEX = re.compile(r":param (?P<name>[*\w]+): (?P<doc>.*?)"
                         r"(?:(?=:param)|(?=:return)|(?=:raises)|\Z)", re.S)


class DocString(typing.NamedTuple):
    short_description: str
    long_description: str
    params: dict


def trim(docstring):
    """trim function from PEP-257"""
    if not docstring:
        return ""
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return "\n".join(trimmed)


def reindent(string):
    return "\n".join(l.strip() for l in string.strip().split("\n"))


def parse_docstring(docstring):
    """Parse the docstring into its components."""

    short_description = long_description = ""
    params = {}

    if docstring:
        docstring = trim(docstring)
        lines = docstring.split("\n", 1)
        short_description = lines[0]
        if len(lines) > 1:
            long_description = lines[1].strip()
            params_returns_desc = None
            match = PARAM_OR_RETURNS_REGEX.search(long_description)
            if match:
                long_desc_end = match.start()
                params_returns_desc = long_description[long_desc_end:].strip()
                long_description = long_description[:long_desc_end].rstrip()
            if params_returns_desc:
                params = {
                    name: trim(doc) for name, doc in PARAM_REGEX.findall(params_returns_desc)
                }

    return DocString(short_description, long_description, params)
