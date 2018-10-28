import typing

from stark.compat import jinja2
from stark.utils import get_vdirs


def get_jinja_template_loader(dirs, loaders=None):
    loaders = (loaders or []) + [jinja2.FileSystemLoader(t) for t in dirs]
    return jinja2.ChoiceLoader(loaders) if len(loaders) > 1 else loaders[0]


class BaseTemplates():
    def render_template(self, path: str, **context):
        raise NotImplementedError()


class Templates(BaseTemplates):
    def __init__(self,
                 template_dirs: typing.Union[str, list, tuple, dict],
                 global_context: dict = None):
        if jinja2 is None:
            raise RuntimeError('`jinja2` must be installed to use `Templates`.')

        global_context = global_context if global_context else {}

        template_dirs = get_vdirs(template_dirs)
        root_template_dirs = template_dirs.pop('', None)

        loader = None
        if template_dirs:
            loader = jinja2.PrefixLoader({
                prefix: get_jinja_template_loader(dirs)
                for prefix, dirs in template_dirs.items() if dirs
            })

        if root_template_dirs:
            loader = get_jinja_template_loader(root_template_dirs, [loader] if loader else None)

        self.env = jinja2.Environment(autoescape=True, loader=loader)
        for key, value in global_context.items():
            self.env.globals[key] = value

    def render_template(self, path: str, **context):
        template = self.env.get_template(path)
        return template.render(**context)
