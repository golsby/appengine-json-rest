import logging
import sys

from google.appengine.ext import db

from converter import DictionaryConverter
from errors import ModelNotRegisteredError, ObjectMissingError


__author__ = 'Brian'


__registered_models = {}


def register_model(model, converter=None, prefix_with_package_path=False):
    """
    Registers the given db.Model class with the REST API.

    Exceptions:
        KeyError if model has already been registered.

    Arguments:
        model: db.Model class to be registered.

        converter: Optional class to handle conversion of models to
            and from a dict using json.loads() and json.dumps()

        prefix_with_package_path:
            Causes models to be registered with their full path instead
            of just their name. This is useful if you experience name
            collisions of models in different packages.
    """
    if isinstance(model, type) and issubclass(model, db.Model):
        model_name = ''
        if prefix_with_package_path:
            model_name += model.__module__ + '.'
        model_name += model.__name__

        if __registered_models.get(model_name):
            raise KeyError('Model with name {0} already registered'.format(model_name))
        __registered_models[model_name] = (model, converter or DictionaryConverter())


def register_models_from_module(model_module, prefix_with_package_path=False, exclude_model_types=None, recurse=False):
    """
    Adds all models from the given module to this request handler.
    The name of the Model class will be used as the REST path for Models
    of that type (optionally including the module name).

    REST paths which conflict with previously added paths will cause a
    KeyError.

    Args:

        model_module: a module instance or the name of a module instance
            (e.g. use __name__ to add models from the current module instance)
        use_module_name: True to include the name of the module as part of
            the REST path for the Model, False to use the Model name alone
            (this may be necessary if Models with conflicting names are used
            from different modules).
        exclude_model_types: optional list of Model types to be excluded
            from the REST handler.
        recurse: True to recurse into sub-modules when searching for
            Models, False otherwise

    """
    logging.info("adding models from module %s", model_module)
    if not exclude_model_types:
        exclude_model_types = []
    if isinstance(model_module, basestring):
        model_module = __import__(model_module)
    for obj_name in dir(model_module):
        obj = getattr(model_module, obj_name)
        if isinstance(obj, type(sys)):
            # only import "nested" modules, otherwise we get the whole
            # world and bad things happen
            if recurse and obj.__name__.startswith(model_module.__name__ + "."):
                register_models_from_module(obj, prefix_with_package_path, exclude_model_types, recurse)

        register_model(obj, prefix_with_package_path=prefix_with_package_path)


def get_registered_model_names():
    names = []
    for registered_model in __registered_models:
        names.append(registered_model)
    return names


def get_registered_model_type(model_name):
    (model_class, converter) = __registered_models.get(model_name)
    if not model_class:
        raise ModelNotRegisteredError(model_name)

    return model_class, converter


def get_registered_model_instance(model_name, key):
    (model_class, converter) = get_registered_model_type(model_name)

    try:
        id_ = int(key)
        try:
            model = model_class.get_by_id(id_)
            if not model:
                raise ObjectMissingError('{0} with id {1} not found'.format(model_name, id_))
        except:
            raise ObjectMissingError('{0} with id {1} not found'.format(model_name, id_))
    except ValueError:
        try:
            model = model_class.get(key)
        except:
            raise ObjectMissingError('{0} with key {1} not found'.format(model_name, key))

    return model, converter