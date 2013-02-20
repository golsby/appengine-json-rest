"""
Create a REST-ful JSON api for existing AppEngine db.Model classes.

Setup Features:
  * See docs for for create_application() for details.
  * Create your REST URL at any location in your App Engine app.
  * Register models individually (see register_model())
  * Register all models in a module - recursively, if you want
    (see register_models_from_module())
  * Custom authentication/authorization function to restrict access to your API.
  * Require HTTPS (added as a double layer of safety in case you use basic
    authentication - be sure to set up your app.yaml property, too).

Usage:
  * Create model:
     Method: HTTP POST
     URL: /rest/ModelName
  * Read model:
     Method: HTTP GET
     URL: /rest/ModelName/id
  * Update model:
     Method: HTTP PUT
     URL: /rest/ModelName/id
  * Delete model:
     Method: HTTP DELETE
     URL: /rest/ModelName/id
  * Search for and page through model:
     Method: HTTP GET
     URL: /rest/ModelName/search
     QueryString Parameters:
       cursor:

  * List names of available models at /rest/metadata
  * Query model-specific fields, types, and other data: /rest/metadata/ModelName

JSON Output Formatting:
    db.DateProperty, db.DateTimeProperty, and db.TimeProperty classes are
    returned as ISO 8601 format. See http://en.wikipedia.org/wiki/ISO_8601

    Successful API calls return data in the form:
        {
          "status": "success",
          "data": obj
        }

        The value of obj depends on the specific API call that is made.

    Errors are returned in the form:
        {
          "status": "error",
          "message": unicode,
          "type": unicode
        }

        message: extended information about the failure.
        type: the class name of the Exception raised during failure


Several ideas and snippets have been borrowed from other open-source projects.
Special thanks to the developers of:
http://code.google.com/p/appengine-rest-server/
http://code.google.com/p/gae-json-rest/
"""
import registry
from handlers import MetadataHandler, SearchHandler, SingleModelHandler, set_authenticator, set_https_required
from google.appengine.ext import webapp


def create_application(prefix, debug=False, auth_func=None, require_https=False, models=None, model_modules=None):
    """
    Create a webapp.WSGIApplication object that handles REST requests at http://host/prefix.

    Arguments:
        prefix:
            URL prefix where your REST api is located. If you want to
            handle requests at http://hostname/my/rest/api/ then prefix is
            "/my/rest/api/"

        debug:
            passed through to webapp.WSGIApplication() ctor

        auth_function:
            Optional function to to authenticate each request.
            Signature: auth(webob.request)

        require_https:
            An extra sanity check to check that the request is
            coming over HTTPS. Useful if you use Basic authentication.

        models:
            List of db.Model classes to register for use in the REST API.

        model_modules:
            List of module names or classes to search recursively for
            db.Model classes. All db.Model classes will be registered
            for use in the REST API.
    """
    prefix = prefix.strip('/')
    set_authenticator(auth_func)
    set_https_required(require_https)

    if models:
        for model in models:
            register_model(model)

    if model_modules:
        for module in model_modules:
            register_models_from_module(module, recurse=True)

    return webapp.WSGIApplication(
        [
            ('/%s/metadata/([^/]+)/?' % prefix, MetadataHandler),
            ('/%s/metadata/?' % prefix, MetadataHandler),
            ('/%s/([^/]+)/search' % prefix, SearchHandler),
            ('/%s/([^/]+)/?' % prefix, SingleModelHandler),
            ('/%s/([^/]+)/([^/]+)/?' % prefix, SingleModelHandler),
            ],
        debug=debug
    )


def register_model(model, converter=None, prefix_with_package_path=False):
    """
    Registers the given db.Model class with the REST API.

    Arguments:
        model: db.Model class to be registered.

        converter: Optional class to handle conversion of models to
            and from a dict using json.loads() and json.dumps()

        prefix_with_package_path:
            Causes models to be registered with their full path instead
            of just their name. This is useful if you experience name
            collisions of models in different packages.
    """
    registry.register_model(model, converter, prefix_with_package_path)


def register_models_from_module(model_module, prefix_with_package_path=False, exclude_model_types=None, recurse=False):
    """
    Adds all models from the given module to this request handler.
    The name of the Model class will be used as the REST path for
    Models of that type (optionally including the module name).

    REST paths which conflict with previously added paths will cause a
    KeyError.

    Args:

      model_module: a module instance or the name of a module instance
                    (e.g. use __name__ to add models from the current
                    module instance)
      use_module_name: True to include the name of the module as part of
                       the REST path for the Model, False to use the
                       Model name alone (this may be necessary if Models
                       with conflicting names are used from different
                       modules).
      exclude_model_types: optional list of Model types to be excluded
                           from the REST handler.
      recurse: True to recurse into sub-modules when searching for
               Models, False otherwise

    """
    registry.register_models_from_module(model_module, prefix_with_package_path, exclude_model_types, recurse)
