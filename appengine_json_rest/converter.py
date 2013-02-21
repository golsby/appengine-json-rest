__author__ = 'Brian'
from google.appengine.ext import db
from dateutil import parser as date_parser


def date_to_str(date):
    return date.isoformat()


def str_to_date(date_string):
    return date_parser.parse(date_string).date()


def datetime_to_str(d):
    return d.isoformat()


def str_to_datetime(s):
    return date_parser.parse(s)


def time_to_str(t):
    return t.isoformat()


def str_to_time(s):
    return date_parser.parse(s).time()


property_converters = {
    db.DateTimeProperty: (datetime_to_str, str_to_datetime),
    db.DateProperty: (date_to_str, str_to_date),
    db.TimeProperty: (time_to_str, str_to_time),
    db.FloatProperty: (float, float),
}


class UnhandledPropertyError(Exception):
    pass


def register_property_converter(property_type, from_property_fn, to_property_fn):
    property_converters[property_type] = (from_property_fn, to_property_fn)


class DictionaryConverter(object):
    '''
    DictionaryConverter is the middle-man between a db.Model class
    and a webapp.RequestHandler that formats the data.

    handlers.JsonHandler will convert between the dict format
    from this class and a JSON string.
    '''
    def __type_from_property(self, model, prop):
        value = getattr(model, prop.name)
        if type(prop) in property_converters:
            return property_converters[type(prop)][0](value)

        return value

    def __property_from_type(self, prop, value):
        if type(prop) in property_converters:
            fn = property_converters[type(prop)][1]
            newval = fn(value)
            return newval

        return value

    # HTTP GET
    def read_model(self, model):
        result = {
            'key': str(model.key()),
            'id': model.key().id()
        }
        for name, prop in model._properties.iteritems():
            result[name] = self.__type_from_property(model, prop)
        return result

    # HTTP PUT (update), Idempotent
    def update_model(self, model, values):
        converted_values = {}
        for (k, v) in values.iteritems():
            prop = model._properties.get(k)
            if prop:
                converted_values[k] = self.__property_from_type(prop, v)

        for k, v in converted_values.iteritems():
            setattr(model, k, v)
        model.put()
        return model.key().id()

    # HTTP POST (create), will create multiple items if called multiple times
    def create_model(self, model_type, values):
        converted_values = {}
        for (k, v) in values.iteritems():
            prop = model_type._properties.get(k)
            if prop:
                converted_values[k] = self.__property_from_type(prop, v)

        model = model_type(**converted_values)
        model.put()
        return model.key().id()

    def metadata(self, cls):
        result = {}
        for name, prop in cls._properties.iteritems():
            prop_data = {
                'required': prop.required,
                'property_class': prop.__module__ + '.' + prop.__class__.__name__
            }

            data_type = prop.data_type
            if data_type.__module__ != '__builtin__':
                prop_data['value_type'] = prop.data_type.__module__ + '.' + prop.data_type.__name__
            else:
                prop_data['value_type'] = prop.data_type.__name__

            if hasattr(prop, 'choices') and prop.choices:
                prop_data['choices'] = prop.choices
            if hasattr(prop, 'multiline'):
                prop_data['multiline'] = prop.multiline
            if hasattr(prop, 'MAX_LENGTH'):
                prop_data['max_length'] = prop.MAX_LENGTH

            result[name] = prop_data

        return result
