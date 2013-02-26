__author__ = 'Brian'
from google.appengine.ext import db
from google.appengine.api import datastore_types
from dateutil import parser as date_parser
import datetime
from importlib import import_module

FROM_PROPERTY = 0
TO_PROPERTY = 1


def from_date(date):
    return date.isoformat()


def to_date(date_string):
    return date_parser.parse(date_string).date()


def from_datetime(d):
    return d.isoformat()


def to_datetime(s):
    return date_parser.parse(s)


def from_time(t):
    return t.isoformat()


def to_time(s):
    return date_parser.parse(s).time()


def from_geopt(p):
    if p:
        return {'lat': p.lat, 'lon': p.lon}
    else:
        return None


def to_geopt(o):
    if not o:
        return None
    if type(o) is dict:
        return db.GeoPt(o.get('lat', 0), o.get('lon', 0))
    if type(o) is list:
        return db.GeoPt(float(o[0]), float(o[1]))

    raise TypeError('Conversion to db.GeoPt expected dict or list; got {0}'.format(type(o)))


def from_refprop(o):
    return {
        "model": type(o).__name__,
        "module": type(o).__module__,
        "id": o.key().id(),
        "key": str(o.key())
    }


def to_refprop(o):
    if type(o) is basestring:
        return db.Model.get(o)

    if type(o) is dict:
        module = import_module(o.get('module'))
        cls = getattr(module, o.get('model'))
        obj = cls.get_by_id(o.get('id'))
        return obj


def from_byte_array(b):
    pass


def to_byte_array(s):
    pass


def identity(o):
    return o


property_converters = {
    db.DateTimeProperty: (from_datetime, to_datetime),
    datetime.datetime: (from_datetime, to_datetime),
    db.DateProperty: (from_date, to_date),
    db.TimeProperty: (from_time, to_time),
    db.FloatProperty: (float, float),
    db.GeoPtProperty: (from_geopt, to_geopt),
    datastore_types.GeoPt: (from_geopt, to_geopt),
    db.ReferenceProperty: (from_refprop, to_refprop),

    # Unsupported Types
    # TODO: Support these unsupported types.
    # TODO: Updated documentation as support comes!
    # db.ListProperty
    # db.StringListProperty
    # db.Key
    # blobstore.BlobKey
    # blobstore.BlobReferenceProperty
    # users.User
    # datastore_types.Blob
    # db.BlobProperty (byte array)
    # datastore_types.ByteString
    # db.ByteStringProperty (byte array)
    # datastore_types.IM (tuple: (protocol(unicode), address(unicode)))
    # db.IMProperty (tuple: (protocol(unicode), address(unicode)))

    # Implicitly supported types
    # datastore_types.Text (unicode)
    # db.TextProperty (unicode)
    # datastore_types.Category (unicode)
    # db.CategoryProperty (unicode)
    # datastore_types.Email (unicode)
    # db.EmailProperty (unicode)
    # datastore_types.Link (unicode)
    # db.LinkProperty (unicode)
    # datastore_types.PhoneNumber (unicode)
    # db.PhoneNumberProperty (unicode)
    # datastore_types.PostalAddress (unicode)
    # db.PostalAddressProperty (unicode)
    # datastore_types.Rating (int)
    # db.RatingProperty (int)
}


def get_property_converter_function(direction, property_type):
    if property_type in property_converters:
        (from_func, to_func) = property_converters[property_type]
        if direction == FROM_PROPERTY:
            return from_func
        else:
            return to_func

    return identity

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
    def __convert_property(self, direction, prop, value):
        if type(prop) is db.ListProperty:
            result = []
            fn = get_property_converter_function(direction, prop.item_type)
            for item in value:
                result.append(fn(item))
            return result

        fn = get_property_converter_function(direction, type(prop))
        return fn(value)

    def _type_from_property(self, model, prop):
        value = getattr(model, prop.name)
        return self.__convert_property(FROM_PROPERTY, prop, value)

    def _property_from_type(self, prop, value):
        return self.__convert_property(TO_PROPERTY, prop, value)

    # HTTP GET
    def read_model(self, model):
        result = {
            'key': str(model.key()),
            'id': model.key().id()
        }
        for name, prop in model._properties.iteritems():
            result[name] = self._type_from_property(model, prop)
        return result

    # HTTP PUT (update), Idempotent
    def update_model(self, model, values):
        converted_values = {}
        for (k, v) in values.iteritems():
            prop = model._properties.get(k)
            if prop:
                converted_values[k] = self._property_from_type(prop, v)

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
                converted_values[k] = self._property_from_type(prop, v)

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
