import json
import os
import re

from google.appengine.ext import webapp

from errors import \
    HttpsRequiredError, \
    ModelNotRegisteredError, \
    ApiFailureError, \
    AuthenticationRequiredError


__author__ = 'Brian'

QUERY_PATTERN = re.compile(r"^(f.._)(.+)$")

QUERY_EXPRS = {
    "feq_": "{0} =",
    "flt_": "{0} <",
    "fgt_": "{0} >",
    "fle_": "{0} <=",
    "fge_": "{0} >=",
    "fne_": "{0} !=",
    "fin_": "{0} IN"}


__authenticator = None
__require_https = True


def authenticate(function):
    """
    Decorator for any webapp.RequestHandler class method.
    Checks for valid API Key in the Authorization header.
    If Authorization header isn't found, the api_key querystring
    or post variable is evaluated.
    """
    def decorated(*args, **kwargs):
        self = args[0]
        localhost = self.request.host.startswith('localhost')
        if self.app.require_https and not localhost:
            if os.environ.get("HTTPS") != 'on':
                raise HttpsRequiredError()

        if self.app.authenticator:
            try:
                self.app.authenticator(self.request)
            except AuthenticationRequiredError:
                self.error(401)
                return

        return function(*args, **kwargs)
    return decorated


def set_https_required(value):
    global __require_https
    __require_https = value


class JsonHandler(webapp.RequestHandler):
    """
    Handles setting Content-Type to application/json
    and returning of consistently formatted JSON results.
    Success responses in the form:
    {
        "status":"success",
        "data":obj
    }

    Error responses in the form:
    {
        "status":"error",
        "type":unicode
        "message":unicode,
    }
    where:
    type is the python class name of the exception raised to indicate error.
    message is extended error information.
    """
    def __init__(self, request, response):
        super(JsonHandler, self).__init__(request, response)
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'

        if self.request.get('pretty'):
            self.indent = 4
        else:
            self.indent = None

    #@requires_authentication
    #def authenticate_caller(self):
    #    '''Call this function if you want to have control over the response when the user is not authenticated.
    #    It's easier to wrap your get, post, put, head, delete methods with @requires_authentication.'''
    #    pass

    def __render_json(self, data):
        self.response.write(json.dumps(data, indent=self.indent))

    def api_success(self, data=None):
        response = {'status': 'success'}
        if data is not None:
            response['data'] = data
        self.__render_json(response)

    def api_fail(self, message=None, data=None, exception_class_name=None):
        response = {'status': 'error'}
        if message:
            response['message'] = message
        if exception_class_name:
            response['type'] = exception_class_name
        if data:
            response['data'] = data
        self.__render_json(response)

    def handle_exception(self, exception, debug):
        import traceback
        import logging

        self.indent = 4

        if issubclass(exception.__class__, ApiFailureError):
            self.api_fail(message=exception.value, exception_class_name=exception.__class__.__name__)
            return
        else:
            message = str(exception)
            data = {'args': exception.args}
            logging.error(exception.args)
            if debug:
                trace = traceback.format_stack()
                data['trace'] = trace
                logging.error("EXCEPTION: %s" % str(trace))

        self.api_fail(message=message, data=data, exception_class_name=exception.__class__.__name__)


class MetadataHandler(JsonHandler):
    """
    Returns Metadata about models registered in this REST API.
    Assuming the application prefix to be "rest", these URLs
    operate as follows:

    GET /rest/metadata:
        Returns {"status":"success", "data":[list of model names]}

    GET /rest/metadata/ModelName:
        Returns {"status":"success", "data":{model_schema_details}}
    """
    @authenticate
    def get(self, modelName=None):
        if modelName:
            (modelClass, converter) = self.app.get_registered_model_type(modelName)
            metadata = converter.metadata(modelClass)
            self.api_success(metadata)
        else:
            self.api_success(self.app.get_registered_model_names())


class SingleModelHandler(JsonHandler):
    """
    Handles Create (POST), Read (GET), Update (PUT), and Delete (DELETE) for a single model.
    See individual handlers below for details.
    """
    @authenticate
    def get(self, modelName, key):
        """
        Usage: HTTP GET to /rest/ModelName/key_or_id
        Returns:
        {
            "status": "success",
            "data": {
                "property_name": property_value,
                ...
            }
        }
        """
        (model, converter) = self.app.get_registered_model_instance(modelName, key)
        self.api_success(converter.read_model(model))

    @authenticate
    def post(self, modelName):
        """
        Create new instance of model.
        Usage: HTTP POST to /rest/ModelName with ContentType=application/json
        Input:
        {
            "property_name": property_value,
            ...
        }
        Returns:
        {
            "status": "success",
            "data": id
        }

        Where id is the numeric integer ID of the newly-created model.
        See the description if id() for details:
        https://developers.google.com/appengine/docs/python/datastore/keyclass#Key_id
        """
        (model_class, converter) = self.app.get_registered_model_type(modelName)
        import urllib
        json_string = urllib.unquote(self.request.body)
        values = json.loads(json_string)

        self.api_success(converter.create_model(model_class, values))

    @authenticate
    def put(self, modelName, key):
        """
        Update existing model with either numeric ID=key or key()=key.
        Usage: HTTP PUT to /rest/ModelName/id_or_key with ContentType=application/json
        Input:
        {
            "property_name": property_value,
            ...
        }
        Returns:
        {
            "status": "success",
            "data": key
        }

        Where key is the passed-in parameter
        """
        (model, converter) = self.app.get_registered_model_instance(modelName, key)
        import urllib
        json_string = urllib.unquote(self.request.body)
        values = json.loads(json_string)

        converter.update_model(model, values)
        try:
            id_ = int(key)
        except TypeError:
            id_ = key

        self.api_success(id_)

    @authenticate
    def delete(self, modelName, key):
        """
        Delete existing model with key().id() == key or key()==key.
        Usage: HTTP DELETE to /rest/ModelName/id_or_key
        Returns:
        {
            "status": "success",
            "data": key
        }

        Where key is the passed-in parameter
        """
        (model, converter) = self.app.get_registered_model_instance(modelName, key)
        model.delete()
        try:
            id_ = int(key)
        except TypeError:
            id_ = key

        self.api_success(id_)


class SearchHandler(JsonHandler):
    """
    Search for model instances of a given model_name.
    Returns:
        Success:
        {
            "status":"success",
            "data"={
                "models": [models],
                "cursor": cursor
        }

        models: a list of dicts of containing model definitions.
        cursor: an opaque string to be passed back to Search handler for subsequent pages.
            null if there are no more models to query

        Failure: {"status":"error", "message"=error_detail}

    Querystring Parameters:
        Filter Expression:
            Querystring Name is of the form "operator_property" where "property" is the property
            to filter by. operator is one of:
              - "feq": equality filter
              - "flt": less-than filter
              - "fgt": greater-than filter
              - "fle": less-than-or-equal filter
              - "fge": greater-than-or-equal filter
              - "fne": not-equal filter

        Sort Order:
            Querystring name: "order"
            Querystring value: property to sort
            To sort descending, prefix property name with "-"
            Example: "order=-LastName" sorts by model's LastName property, descending

        Cursor:
            Querystring name: "cursor"
            Querystring value: cursor value from previous call.

        Page Size:
            Querystring name: "limit"
            Querystring value: integer specifying number of results per query.
            Note: AppEngine has a hard limit of 1,000 models, and the request
                  may time out before 1,000 models due to processing overhead.

    """
    @authenticate
    def get(self, model_name):
        try:
            (modelClass, converter) = self.app.get_registered_model_type(model_name)
        except TypeError:
            raise ModelNotRegisteredError(model_name)

        data = {
            'models': []
        }
        query = modelClass.all()
        limit = 20
        for arg in self.request.arguments():
            match = QUERY_PATTERN.match(arg)
            if match:
                query_type = match.group(1)
                query_property = match.group(2)
                operator = QUERY_EXPRS.get(query_type)
                prop = modelClass._properties.get(query_property)
                value = converter.__property_from_type(prop, arg)
                query.filter(operator.format(query_property), value)
                continue
            if arg == 'order':
                query.order(self.request.get(arg))
                continue
            if arg == 'cursor':
                query.with_cursor(self.request.get(arg))
                continue
            if arg == 'limit':
                try:
                    limit = int(self.request.get(arg))
                    continue
                except ValueError:
                    raise ApiFailureError('limit parameter must be an integer')

        models = query.fetch(limit)
        data['cursor'] = None
        if len(models) == limit:
            data['cursor'] = query.cursor()
        for model in models:
            data['models'].append(converter.read_model(model))
        self.api_success(data)