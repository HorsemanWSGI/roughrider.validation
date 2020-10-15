class _FactoryMeta(type):

    def __getitem__(self, params):
        return Factory(params)


class Factory(metaclass=_FactoryMeta):

    __slots__ = ('model', )

    def __init__(self, model):
        self.model = model

    def __call__(self, request, **bindable):
        return self.model.instanciate(request, **bindable)

    def __get_validators__(self):
        yield self.model.validate

    def validate(self, v):
        if not isinstance(v, self.model):
            raise TypeError('{self.model} required')
        return v

    def __modify_schema__(self, field_schema):
        self.model.__modify_schema__(field_schema)


class Validatable:

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, cls):
            raise TypeError('Request required')
        return v

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update({
            'title': cls.__name__
        })
