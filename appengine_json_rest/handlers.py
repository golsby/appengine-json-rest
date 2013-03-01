import json
import os
import re
import logging
import webapp2

from google.appengine.ext import webapp

import errors


__author__ = 'Brian'

QUERY_PATTERN = re.compile(r"^(f.._)(.+)$")

QUERY_EXPRS = {
    "feq_": "{0} =",
    "flt_": "{0} <",
    "fgt_": "{0} >",
    "fle_": "{0} <=",
    "fge_": "{0} >=",
    "fne_": "{0} !="}


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
        if webapp2.get_app().require_https and not localhost:
            if os.environ.get("HTTPS") != 'on':
                raise errors.HttpsRequiredError()

        if webapp2.get_app().authenticator:
            try:
                webapp2.get_app().authenticator(self.request)
            except errors.AuthenticationRequiredError as exception:
                if not exception.headers or not exception.headers.get('WWW-Authenticate'):
                    # A WWW-Authenticate header is required; without it the negotiation for authentication fails.
                    logging.error('AuthenticationRequiredException must pass a WWW-Authenticate header.')
                    self.error(500)
                    return
                self.response.headers.update(exception.headers)
                self.error(401)
                return
            except errors.ForbiddenError:
                self.error(403)
                return

        return function(*args, **kwargs)
    return decorated


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

    def __render_json(self, data):
        self.response.write(json.dumps(data, indent=self.indent))

    def api_success(self, data=None):
        response = {'status': 'success'}
        if data is not None:
            response['data'] = data
        self.__render_json(response)

    def api_fail(self, message=None, data=None, exception_class_name=None, status_code=404):
        response = {'status': 'error'}
        if message:
            response['message'] = message
        if exception_class_name:
            response['type'] = exception_class_name
        if data:
            response['data'] = data
        self.response.set_status(status_code)
        self.__render_json(response)

    def set_location_header(self, model):
        self.response.headers["Location"] = "{0}/{1}".format(self.request.path, model.key().id())

    def handle_exception(self, exception, debug):
        import traceback
        import logging

        self.indent = 4

        if type(exception) is errors.ObjectMissingError:
            self.api_fail(message=exception.value, exception_class_name=exception.__class__.__name__, status_code=404)
            return
        if issubclass(exception.__class__, errors.ApiFailureError):
            self.api_fail(message=exception.value, exception_class_name=exception.__class__.__name__, status_code=500)
            return
        else:
            message = str(exception)
            logging.error(exception.args)
            if debug:
                trace = traceback.format_stack()
                data = {'trace': trace}
                logging.error("EXCEPTION: %s" % str(trace))
            else:
                data = None

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
            modelClass = webapp2.get_app().get_registered_model_type(modelName)
            metadata = webapp2.get_app().converter.metadata(modelClass)
            self.api_success(metadata)
        else:
            models = webapp2.get_app().get_registered_model_names()
            data = []
            for model in models:
                data.append(
                    {
                        'name': model,
                        'url': '{0}{1}'.format(self.request.host_url, webapp2.get_app().model_url(model)),
                        'metadata_url': '{0}/metadata'.format(webapp2.get_app().model_url(model))
                    }
                )
            self.api_success(data)


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
        model = webapp2.get_app().get_registered_model_instance(modelName, key)
        self.api_success(webapp2.get_app().converter.read_model(model))

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
        model_class = webapp2.get_app().get_registered_model_type(modelName)
        import urllib
        json_string = urllib.unquote(self.request.body)
        values = json.loads(json_string)

        model = webapp2.get_app().converter.create_model(model_class, values)
        self.response.set_status(201)
        self.set_location_header(model)
        self.api_success(webapp2.get_app().converter.read_model(model))

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
        model = webapp2.get_app().get_registered_model_instance(modelName, key)
        import urllib
        json_string = urllib.unquote(self.request.body)
        values = json.loads(json_string)

        model = webapp2.get_app().converter.update_model(model, values)
        self.set_location_header(model)
        self.api_success(webapp2.get_app().converter.read_model(model))

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
        model = webapp2.get_app().get_registered_model_instance(modelName, key)
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
            modelClass = webapp2.get_app().get_registered_model_type(model_name)
        except TypeError:
            raise errors.ModelNotRegisteredError(model_name)

        data = {
            'models': []
        }
        query = modelClass.all()
        next_page_querystring = ''
        limit = 20
        for arg in self.request.arguments():
            match = QUERY_PATTERN.match(arg)
            if match:
                next_page_querystring += "&{0}={1}".format(arg, self.request.get(arg))
                query_type = match.group(1)
                query_property = match.group(2)
                operator = QUERY_EXPRS.get(query_type)
                prop = modelClass._properties.get(query_property)
                value = webapp2.get_app().converter._property_from_type(prop, self.request.get(arg))
                query.filter(operator.format(query_property), value)
                continue
            if arg == 'order':
                next_page_querystring += "&{0}={1}".format(arg, self.request.get(arg))
                query.order(self.request.get(arg))
                continue
            if arg == 'cursor':
                query.with_cursor(self.request.get(arg))
                continue
            if arg == 'limit':
                try:
                    limit = int(self.request.get(arg))
                    next_page_querystring += "&{0}={1}".format(arg, self.request.get(arg))
                    continue
                except ValueError:
                    raise errors.ApiFailureError('limit parameter must be an integer')

        models = query.fetch(limit)

        data['cursor'] = None
        if len(models) == limit:
            data['cursor'] = query.cursor()
            next_page_querystring += "&cursor=" + query.cursor()
            data['next_page'] = "{0}{1}?{2}".format(self.request.host_url, self.request.path, next_page_querystring[1:])
        for model in models:
            data['models'].append(webapp2.get_app().converter.read_model(model))
        self.api_success(data)