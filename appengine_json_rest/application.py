__author__ = 'Brian'
from webapp2 import WSGIApplication
from google.appengine.ext import db
from converter import DictionaryConverter
import handlers
import errors
import logging
import sys


class JSONApplication(WSGIApplication):
    """

    """
    def __init__(self, prefix, auth_func=None, require_https=False, models=None, model_modules=None, debug=False, config=None):
        routes = [
            ('/%s/metadata/([^/]+)/?' % prefix, handlers.MetadataHandler),
            ('/%s/metadata/?' % prefix, handlers.MetadataHandler),
            ('/%s/([^/]+)/search' % prefix, handlers.SearchHandler),
            ('/%s/([^/]+)/?' % prefix, handlers.SingleModelHandler),
            ('/%s/([^/]+)/([^/]+)/?' % prefix, handlers.SingleModelHandler),
        ]

        super(JSONApplication, self).__init__(routes, debug, config)
        self.require_https = require_https
        self.authenticator = auth_func
        self.__registered_models = {}
        self.__property_converters = {}

        if models:
            for model in models:
                self.register_model(model)

        if model_modules:
            for module in model_modules:
                self.register_models_from_module(module, recurse=True)

    def register_model(self, model, converter=None, prefix_with_package_path=False):
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

            if self.__registered_models.get(model_name):
                raise KeyError('Model with name {0} already registered'.format(model_name))
            self.__registered_models[model_name] = (model, converter or DictionaryConverter())

    def register_models_from_module(self, model_module, prefix_with_package_path=False, exclude_model_types=None, recurse=False):
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
                    self.register_models_from_module(obj, prefix_with_package_path, exclude_model_types, recurse)

            self.register_model(obj, prefix_with_package_path=prefix_with_package_path)

    def get_registered_model_names(self):
        names = []
        for registered_model in self.__registered_models:
            names.append(registered_model)
        return names

    def get_registered_model_type(self, model_name):
        (model_class, converter) = self.__registered_models.get(model_name)
        if not model_class:
            raise errors.ModelNotRegisteredError(model_name)

        return model_class, converter

    def get_registered_model_instance(self, model_name, key):
        (model_class, converter) = self.get_registered_model_type(model_name)

        try:
            id_ = int(key)
            try:
                model = model_class.get_by_id(id_)
                if not model:
                    raise errors.ObjectMissingError('{0} with id {1} not found'.format(model_name, id_))
            except:
                raise errors.ObjectMissingError('{0} with id {1} not found'.format(model_name, id_))
        except ValueError:
            try:
                model = model_class.get(key)
            except:
                raise errors.ObjectMissingError('{0} with key {1} not found'.format(model_name, key))

        return model, converter