import inspect
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
        self.__signature__ = inspect.signature(endpoint)

    def __call__(self, overhead: horseman.meta.Overhead):
        params = overhead.environ.get('horseman.path.params', {})
        if content_type := overhead.environ.get('CONTENT_TYPE'):
            form, files = horseman.parsing.parse(
                overhead.environ['wsgi.input'], content_type)
            bindable = {**form.to_dict(), **files.to_dict(), **params}
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
                    to_bind[name] = annotation(overhead, **bindable)
                elif type(annotation) is ModelMetaclass:
                    to_bind[name] = annotation(**bindable)
                elif inspect.isclass(annotation) and issubclass(
                        annotation, horseman.meta.Overhead):
                    to_bind[name] = overhead
                elif name in bindable:
                    to_bind[name] = bindable[name]

            bound = self.__signature__.bind_partial(**to_bind)
            return self.endpoint(*bound.args, **bound.kwargs)
        except LookupError as e:
            return horseman.response.Response.create(404, body=str(e))
        except ValidationError as e:
            return horseman.response.Response.create(
                400, e.json(),
                headers={'Content-Type': 'application/json'})
        except KeyError:
            return horseman.response.Response.create(400)
