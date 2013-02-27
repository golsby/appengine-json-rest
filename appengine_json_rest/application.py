__author__ = 'Brian'
from webapp2 import WSGIApplication
from google.appengine.ext import db
from converter import DictionaryConverter
import handlers
import errors
import logging
import importlib
from types import ModuleType


class JSONApplication(WSGIApplication):
    """
    Parameters:
        auth_func: function that takes a WebOb.request
        Should raise errors.AuthenticationRequiredException or errors.AuthenticationFailedException appropriately.
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
        self.__models_by_name = {}
        self.__models_by_type = {}
        self.__property_converters = {}
        self.root_url = "/{0}".format(prefix)

        if models:
            for model in models:
                self.register_model(model)

        if model_modules:
            for module in model_modules:
                self.register_models_from_module(module, recurse=True)

    @staticmethod
    def _full_path(obj):
        if not hasattr(obj, "__module__"):
            return obj.__name__

        return obj.__module__ + '.' + obj.__name__

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
            model_name = model.__name__
            if prefix_with_package_path:
                model_name = self._full_path(model)

            logging.info("Registering model '{0}' as '{1}'".format(self._full_path(model), model_name))

            already_registered_model = self.__models_by_name.get(model_name)
            if already_registered_model:
                if self._full_path(already_registered_model[0]) == self._full_path(model):
                    logging.debug("Model already registered: " + self._full_path(model))
                    return  # Don't error if we're importing the same model with the same name.
                raise KeyError('Model with name {0} already registered'.format(model_name))
            self.__models_by_name[model_name] = (model, converter or DictionaryConverter())
            self.__models_by_type[model] = (model_name, converter or DictionaryConverter())

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
        logging.debug("adding models from module %s", model_module)
        if not exclude_model_types:
            exclude_model_types = []
        if isinstance(model_module, basestring):
            model_module = importlib.import_module(model_module)
        for obj_name in dir(model_module):
            obj = getattr(model_module, obj_name)
            if isinstance(obj, ModuleType):
                # If we get here, obj is a Module, so we'll try to register models within it.
                if recurse and self._full_path(obj).startswith(self._full_path(model_module)):
                    logging.debug("Recursively registering {0} because it starts with {1}".format(self._full_path(obj), self._full_path(model_module)))
                    self.register_models_from_module(obj, prefix_with_package_path, exclude_model_types, recurse)

            self.register_model(obj, prefix_with_package_path=prefix_with_package_path)

    def get_registered_model_names(self):
        names = []
        for model_names in self.__models_by_name:
            names.append(model_names)
        return names

    def get_registered_model_type(self, model_name):
        (model_class, converter) = self.__models_by_name.get(model_name, (None, None))
        if not model_class:
            raise errors.ModelNotRegisteredError(model_name)

        return model_class, converter

    def get_registered_name(self, model_obj):
        (model_name, converter) = self.__models_by_type.get(model_obj, (None, None))
        if not model_name:
            raise errors.ModelNotRegisteredError(model_obj.__name__)

        return model_name

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