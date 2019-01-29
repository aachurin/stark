import typing

from stark.compat import jinja2
from stark.utils import get_path


def get_jinja_prefix_loader(dirs):
    return jinja2.PrefixLoader({
        prefix: get_jinja_path_loader(path)
        for prefix, path in dirs.items()
    })


def get_jinja_path_loader(dir):
    return jinja2.FileSystemLoader(get_path(dir))


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

        if not isinstance(template_dirs, (list, tuple)):
            template_dirs = [template_dirs]

        loaders = []
        for template_dir in template_dirs:
            if isinstance(template_dir, dict):
                loaders.append(get_jinja_prefix_loader(template_dir))
            else:
                loaders.append(get_jinja_path_loader(template_dir))

        loader = jinja2.ChoiceLoader(loaders) if len(loaders) > 1 else loaders[0]

        self.env = jinja2.Environment(autoescape=True, loader=loader)
        for key, value in global_context.items():
            self.env.globals[key] = value

    def render_template(self, path: str, **context):
        template = self.env.get_template(path)
        return template.render(**context)
