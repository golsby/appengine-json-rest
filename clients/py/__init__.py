import urllib
import urllib2
import json
import base64
import re


class QueryLockedError(Exception):
    pass


class ApiCallFailedError(Exception):
    pass


class ObjectMissingError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class AuthenticationRequiredError(Exception):
    pass


class OperatorNotFoundError(Exception):
    pass


class Query(object):
    """
    The Query object provides methods to create api search
    queries without having to form the HTTP querystring manually.

    Methods:
        * filter: specify search terms to limit results.
            You must restrict your filters to be compatible with the indexes available on AppEngine.
        * order: specify a property used to order results.
        * with_cursor: specify a cursor used previously with the same order and filter to fetch additional results.
        * fetch: fetch data from the remote API. Fetch returns a list of models, or None when no models are available.
            If the remote API returns a cursor, indicating that more results are available, fetch will store that
            cursor and use it for subsequent calls.

    Usage:
        client = JSONClient("ModelName", "http://host/rest")
        query = client.all().filter("name =", "Fred").filter("age <", 65).order("age", descending=True)
        models = query.fetch(10)
        while models:
            # do something with models
            models = query.fetch()  # fetch next batch of models
    """
    FILTER_METHODS = {
        '=': 'feq_',
        '>': 'fgt_',
        '>=': 'fge_',
        '<': 'flt_',
        '<=': 'fle_',
        '!=': 'fne_'
    }

    def __init__(self, client, querystring=None):
        self.__client = client
        self.__params = []
        self.__data_was_fetched = False
        self.__querystring = querystring

    def filter(self, expression, value):
        """
        Adds a filter to the API call

        Returns:
            self to support method chaining
        """
        if self.__data_was_fetched:
            raise QueryLockedError("Query objects cannot be reused, except to call fetch() multiple times when paging through recordsets.")

        if not ' ' in expression:
            raise OperatorNotFoundError("Operator not found in expression '{0}'. (Are you missing a space between the property name and the operator?)".format(expression))

        (prop, operator) = expression.split(' ')
        prefix = Query.FILTER_METHODS.get(operator)
        if prefix:
            self.__params.append(('{0}{1}'.format(prefix, prop), value))
        else:
            raise OperatorNotFoundError('Unsupported operator: ' + operator)

        return self

    def order(self, prop, descending=False):
        if self.__data_was_fetched:
            raise QueryLockedError("Query objects cannot be reused, except to call fetch() multiple times when paging through recordsets.")

        if descending:
            self.__params.append(('order', '-' + prop))
        else:
            self.__params.append(('order', prop))
        return self

    def with_cursor(self, cursor):
        if self.__data_was_fetched:
            raise QueryLockedError("Query objects cannot be reused, except to call fetch() multiple times when paging through recordsets.")

        self.__params.append(('cursor', cursor))
        return self

    def fetch(self, limit=None):
        if limit:
            try:
                limit = int(limit)
            except TypeError:
                raise ValueError('limit must be an int')

            self.__params.append(('limit', limit))

        if self.__querystring:
            querystring = self.__querystring
        else:
            if self.__data_was_fetched:
                return []

            querystring = ''
            for (key, value) in self.__params:
                if querystring:
                    querystring += "&"
                querystring += "{0}={1}".format(self.encode(key), self.encode(value))

        (models, cursor, next_page) = self.__client.search(querystring)
        self.__data_was_fetched = True
        if cursor:
            querystring = re.sub('cursor=[^?&]+&?', '', querystring)
            querystring = querystring.rstrip('&')
            querystring += '&cursor=' + cursor
            self.__querystring = querystring
        else:
            self.__querystring = None
        return models

    def encode(self, s):
        utf8 = unicode(s).encode('utf-8')
        return urllib.quote(utf8)


class JSONClient(object):
    """
    JSONClient provides methods to Create, Read, Update, and Delete individual models from the remote API.
    """
    def __init__(self, model_name, api_root):
        self.headers = {}
        self.model_name = model_name
        self.api_root = api_root

    def authenticate(self):
        """
        Override this method in a base class to perform appropriate authentication handshake and set
        authenticated headers.
        """
        pass

    def api_url(self, id_=None):
        url = self.api_root + self.model_name
        if id_:
            url += '/' + str(id_)
        return url

    def create(self, data):
        """Create a new instance of Model. Uses HTTP POST."""
        return self.__call_json_api(self.api_url(), payload_params=data, method='POST')

    def read(self, id_):
        """
        Get an existing instance of a Model. Uses HTTP GET.
        Parameters:
          id_: Model.key().id()
        """
        return self.__call_json_api(self.api_url(id_), method='GET')

    def update(self, id_, data):
        """
        Update an existing instance of a Model. Uses HTTP PUT.
        Parameters:
          id_: Model.key().id()
        """
        return self.__call_json_api(self.api_url(id_), payload_params=data, method='PUT')

    def delete(self, id_):
        """
        Delete an existing instance of a Model. Uses HTTP DELETE.
        Parameters:
          id_: Model.key().id()
        """
        return self.__call_json_api(self.api_url(id_), method='DELETE')

    def all(self):
        """
        Return a Query instance that can be used to search for instances of this Model.
        """
        return Query(self)

    def search(self, querystring):
        """
        Returns ([models], cursor, next_page_url)

        It's much easier to use the Query class to deal with the results for you.
        """
        data = self.__call_json_api(self.api_url("search"), querystring=querystring)
        return data.get('models'), data.get('cursor'), data.get('next_page')

    def __call_json_api(self, api_path, query_params=None, payload_params=None, querystring=None, method='GET'):
        """
        Low-level method to package up query string, post data, and make the appropriate HTTP REST API call.
        """
        self.authenticate()

        data = None
        if payload_params:
            data = json.dumps(payload_params)

        if querystring and query_params:
            raise ValueError("Only one of query_string and query_params may be passed")

        if query_params:
            querystring = JSONClient.urlencode_multidict(query_params)
        url = api_path

        if method == 'GET' and querystring:
            url += "?" + querystring

        headers = {
            'Content-Type': 'application/json, charset=utf-8',
        }
        headers.update(self.headers)

        request = urllib2.Request(url, data, headers)
        request.get_method = lambda: method
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as ex:
            if ex.code == 403:
                raise ForbiddenError()
            if ex.code == 401:
                raise AuthenticationRequiredError()
            if ex.code == 404:
                raise ObjectMissingError()
            raise

        body = response.read()

        result = json.loads(body)
        if result.get('status') != 'success':
            if result.get('type') == 'ObjectMissingError':
                raise ObjectMissingError(result.get('message'))
            if result.get('type') == 'AuthenticationFailedError':
                raise ForbiddenError()

            raise ApiCallFailedError('API Call Failed: ' + str(body))

        data = result.get('data')
        return data

    @staticmethod
    def urlencode_multidict(data):
        """UTF-8 Encode and then URL Encode WebOb.MultiDict (http://docs.webob.org/en/latest/#multidict)"""
        if not data:
            return None
        import urllib
        utf8_encoded = {}
        for key in sorted(data.keys()):
            # it would be fun to see how to do this using nested list comprehension.
            # not sure if it is more readable, but would be cool :)
            utf8key = unicode(key).encode('utf-8')
            if hasattr(data, 'getall'):
                value = data.getall(key)
                utf8_encoded[utf8key] = [unicode(x).encode('utf-8') for x in value]
            else:
                value = data.get(key)
                if value is None:
                    utf8_encoded[utf8key] = ''
                else:
                    utf8_encoded[utf8key] = unicode(value).encode('utf-8')
        return urllib.urlencode(utf8_encoded, doseq=True)


class BasicAuthJSONClient(JSONClient):
    def __init__(self, model_name, api_root, username=None, password=None):
        super(BasicAuthJSONClient, self).__init__(model_name, api_root)
        self.username = username
        self.password = password

    def authenticate(self):
        if self.username and self.password:
            self.headers['Authorization'] = "Basic " + base64.b64encode('{0}:{1}'.format(self.username, self.password))



