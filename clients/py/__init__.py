import urllib
import urllib2
import json
import base64


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
    FILTER_METHODS = {
        '=': 'feq_',
        '>': 'fgt_',
        '>=': 'fge_',
        '<': 'flt_',
        '<=': 'fle_',
        '!=': 'fne_'
    }

    def __init__(self, client):
        self.client = client
        self.params = []

    def filter(self, expression, value):
        """
        Adds a filter to the API call

        Returns:
            self to support method chaining
        """
        if not ' ' in expression:
            raise OperatorNotFoundError("Operator not found in expression '{0}'. (Are you missing a space between the property name and the operator?)".format(expression))

        (prop, operator) = expression.split(' ')
        prefix = Query.FILTER_METHODS.get(operator)
        if prefix:
            self.params.append(('{0}{1}'.format(prefix, prop), value))
        else:
            raise OperatorNotFoundError('Unsupported operator: ' + operator)

        return self

    def order(self, prop, descending=False):
        if descending:
            self.params.append(('order', '-' + prop))
        else:
            self.params.append(('order', prop))
        return self

    def with_cursor(self, cursor):
        self.params.append(('cursor', cursor))
        return self

    def fetch(self, limit=None):
        if limit:
            try:
                limit = int(limit)
            except TypeError:
                raise ValueError('limit must be an int')

            self.params.append(('limit', limit))

        querystring = ''
        for (key, value) in self.params:
            if querystring:
                querystring += "&"
            querystring += "{0}={1}".format(self.encode(key), self.encode(value))

        return self.client.search(querystring)

    def encode(self, s):
        utf8 = unicode(s).encode('utf-8')
        return urllib.quote(utf8)


class JSONClient(object):
    def __init__(self, model_name, api_root, headers=None, username=None, password=None):
        self.username = username
        self.password = password
        self.headers = headers or {}
        self.model_name = model_name
        self.api_root = api_root

    def api_url(self, id_=None):
        url = self.api_root + self.model_name
        if id_:
            url += '/' + str(id_)
        return url

    def create(self, data):
        return self._call_json_api(self.api_url(), payload_params=data, method='POST')

    def read(self, id_):
        return self._call_json_api(self.api_url(id_), method='GET')

    def update(self, id_, data):
        return self._call_json_api(self.api_url(id_), payload_params=data, method='PUT')

    def delete(self, id_):
        return self._call_json_api(self.api_url(id_), method='DELETE')

    def all(self):
        return Query(self)

    def search(self, querystring):
        data = self._call_json_api(self.api_url("search"), querystring=querystring)
        return data.get('models'), data.get('cursor'), data.get('next_page')

    def _call_json_api(self, api_path, query_params=None, payload_params=None, querystring=None, method='GET'):
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
        if self.username and self.password:
            headers['Authorization'] = "Basic " + base64.b64encode('{0}:{1}'.format(self.username, self.password))

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


