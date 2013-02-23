import urllib2
import json
import base64


class ApiCallFailedError(Exception):
    pass


class ObjectMissingError(Exception):
    pass


class AuthenticationFailedError(Exception):
    pass


class JSONClient(object):
    def __init__(self, model_name, api_root, headers=None, username=None, password=None):
        self.username = username
        self.password = password
        self.headers = headers or {}
        self.model_name = model_name
        self.api_root = api_root

    def create(self, data):
        url = self.api_root + self.model_name
        return self.__call_json_api(url, payload=data, method='POST')

    def read(self, id_):
        url = '{0}{1}/{2}'.format(self.api_root, self.model_name, id_)
        return self.__call_json_api(url, method='GET')

    def update(self, id_, data):
        url = '{0}{1}/{2}'.format(self.api_root, self.model_name, id_)
        return self.__call_json_api(url, payload=data, method='PUT')

    def delete(self, id_):
        url = '{0}{1}/{2}'.format(self.api_root, self.model_name, id_)
        return self.__call_json_api(url, method='DELETE')

    def search(self, limit=None, cursor=None):
        url = '{0}{1}/search'.format(self.api_root, self.model_name)
        querystring = {}
        if limit:
            querystring['limit'] = limit
        if cursor:
            querystring['cursor'] = cursor

        data = self.__call_json_api(url, query_string=querystring)
        return data['models'], data['cursor']

    def __call_json_api(self, api_path, query_string=None, payload=None, method='GET'):
        data = None
        if payload:
            data = json.dumps(payload)
        query_string = JSONClient.urlencode_multidict(query_string)
        url = api_path

        if method == 'GET' and query_string:
            url += "?" + query_string

        headers = {
            'Content-Type': 'application/json, charset=utf-8',
        }
        headers.update(self.headers)
        if self.username and self.password:
            headers['Authorization'] = "Basic " + base64.b64encode('{0}:{1}'.format(self.username, self.password))

        request = urllib2.Request(url, data, headers)
        request.get_method = lambda: method
        response = urllib2.urlopen(request)
        body = response.read()

        result = json.loads(body)
        if result.get('status') != 'success':
            if result.get('type') == 'ObjectMissingError':
                raise ObjectMissingError(result.get('message'))
            if result.get('type') == 'AuthenticationFailedError':
                raise AuthenticationFailedError()

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


