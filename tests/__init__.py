import unittest
import urllib2
import json


# These tests are designed to work with the sample
# AppEngine project wrapping the appengine_json_rest module.
# https://github.com/golsby/appengine-json-rest-sample

api_host = "localhost:5000"
api_root = "http://{0}/simple/".format(api_host)


class ApiCallFailedException(Exception):
    pass


class ObjectMissingException(Exception):
    pass


class JsonApi(object):
    def __init__(self, model_name, api_root):
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

    @staticmethod
    def __call_json_api(api_path, query_string=None, payload=None, method='GET'):
        data = None
        if payload:
            data = json.dumps(payload)
        query_string = JsonApi.urlencode_multidict(query_string)
        url = api_path

        if method == 'GET' and query_string:
            url += "?" + query_string

        headers = {
            'Content-Type': 'application/json, charset=utf-8',
        }

        request = urllib2.Request(url, data, headers)
        request.get_method = lambda: method
        response = urllib2.urlopen(request)
        body = response.read()

        result = json.loads(body)
        if result.get('status') != 'success':
            if result.get('type') == 'ObjectMissingError':
                raise ObjectMissingException(result.get('message'))

            raise ApiCallFailedException('API Call Failed: ' + str(body))

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


class TestSimpleApi(unittest.TestCase):
    def assertDictContainsDict(self, smaller, bigger, exclude_keys=None):
        exclude_keys = exclude_keys or []
        for key in smaller:
            if key in exclude_keys:
                continue

            self.assertEqual(bigger.get(key), smaller.get(key))

    def test_delete_all_fruit(self):
        limit = 2
        Fruit = JsonApi("Fruit", api_root)
        (fruits, cursor) = Fruit.search(limit=limit)
        for fruit in fruits:
            Fruit.delete(fruit['id'])

        while cursor:
            (fruits, cursor) = Fruit.search(limit=limit, cursor=cursor)
            for fruit in fruits:
                Fruit.delete(fruit['id'])

        fruits, cursor = Fruit.search()
        self.assertFalse(fruits, "There should be no fruits after running test_delete_all_fruit")

    def test_CRUD(self):
        data = {
            "name": "Banana",
            "width": 5,
            "location": {"lat": 22.3, "lon": 13.0},
            "destinations": [
                {"lat": 0, "lon": 0},
                {"lat": 1, "lon": 2},
                {"lat": 3.4, "lon": 5.6},
                {"lat": 7, "lon": 8.9},
            ],
            "touched_dates": [
                "2012-01-03T15:32:00",
                "2012-01-04T17:01:16",
                "2012-01-07T00:01:02",
            ]
        }

        Fruit = JsonApi("Fruit", api_root)

        #CREATE
        new_id = Fruit.create(data)

        #READ
        created = Fruit.read(new_id)
        self.assertDictContainsDict(data, created)

        #UPDATE
        created["width"] = 20
        updated_id = Fruit.update(created['id'], created)
        self.assertEquals(new_id, updated_id, "New and Updated IDs don't match")
        updated_model = Fruit.read(updated_id)
        self.assertDictContainsDict(created, updated_model,
                                    exclude_keys=['modified_datetime', 'modified_date', 'modified_time'])

        #DELETE
        Fruit.delete(updated_id)
        try:
            result = Fruit.read(new_id)
            self.assertFalse(True, "Fruit with id {0} should have been deleted!".format(new_id))
        except ObjectMissingException:
            pass
