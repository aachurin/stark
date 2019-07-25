import re
import sys


PARAM_OR_RETURNS_REGEX = re.compile(r":(?:param|returns)")
PARAM_REGEX = re.compile(r":param (?P<name>[*\w]+): (?P<doc>.*?)"
                         r"(?:(?=:param)|(?=:return)|(?=:raises)|\Z)", re.S)


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

    return {
        "short_description": short_description,
        "long_description": long_description,
        "params": params
    }
