import typing
import horseman.meta
import horseman.parsing
import horseman.response

from pydantic import validate_arguments, ValidationError
from pydantic.main import ModelMetaclass

from .types import Factory


class Dispatcher:

    def __init__(self, endpoint: typing.Callable):
        self.endpoint = validate_arguments(endpoint)

    def __call__(self, overhead: horseman.meta.Overhead):
        params = overhead.environ.get('horseman.path.params', {})
        if content_type := overhead.environ.get('CONTENT_TYPE'):
            form, files = horseman.parsing.parse(
                overhead.environ['wsgi.input'], content_type)
            bindable = {**form, **files, **params}
            overhead.set_data({
                'form': form,
                'files': files
            })
        else:
            bindable = {**params}

        to_bind = {}
        try:
            for name, field in self.endpoint.model.__fields__.items():
                annotation = field.type_
                if isinstance(annotation, Factory):
                    to_bind[name] = annotation(request, **bindable)
                elif type(annotation) is ModelMetaclass:
                    to_bind[name] = annotation(**bindable)
                elif issubclass(annotation, horseman.meta.Overhead):
                    to_bind[name] = overhead
                elif name in bindable:
                    to_bind[name] = bindable[name]
            return self.endpoint(**to_bind)
        except ValidationError as e:
            return horseman.response.Response.create(
                400, e.json(),
                headers={'Content-Type': 'application/json'})
        except KeyError:
            return horseman.response.Response.create(400)
