import unittest
import urllib2
import json
import logging

api_host = "localhost:5000"
api_root = "http://{0}/simple/".format(api_host)

__author__ = 'Brian'
def encode_multidict_as_utf8(post):
    '''
    webapp2 stores posted form data as a MultiDict class. MultiDict allows
    the contents of a dictionary to have multiple values, which in turn handles
    post data that looks like "... &p=1&p=2&p=3 ..." while having only one key in
    the dictionary for "p".

    Unicode is poorly supported in python's older libraries such as urllib, used
    extensively to encode and decode form values. That means that passing unicode
    values (such as the ones we get from MultiDict) to urlencode.urlencode()
    can cause exceptions.

    Both urlfetch and taskqueue use urllib internally to convert dicts and MultiDicts
    to usable form. This usually results in problems when we try to post unicode
    data.

    The encode_multidict_as_utf8 creates a dictionary of lists, which can then
    be passed to urlencode.urlencode(dict, doseq=True) to successfully post
    unicode data.
    '''
    result = {}
    for key in sorted(post.keys()):
        # it would be fun to see how to do this using nested list comprehension.
        # not sure if it is more readable, but would be cool :)
        utf8key = unicode(key).encode('utf-8')
        if hasattr(post, 'getall'):
            value = post.getall(key)
            result[utf8key] = [unicode(x).encode('utf-8') for x in value]
        else:
            value = post.get(key)
            if value is None:
                result[utf8key] = ''
            else:
                result[utf8key] = unicode(value).encode('utf-8')

    return result


def urlencode_multidict(data):
    if not data:
        return None
    import urllib
    utf8dict = encode_multidict_as_utf8(data)
    return urllib.urlencode(utf8dict, doseq=True)


class ApiCallFailedException(Exception):
    pass


class ObjectMissingException(Exception):
    pass


def call_json_api(api_path, query_string=None, payload=None, method='GET'):
    data = None
    if payload:
        data = json.dumps(payload)
    query_string = urlencode_multidict(query_string)
    url = api_path

    if method == 'GET' and query_string:
        url += "?" + query_string

    headers = {'Content-Type': 'application/json'}

    request = urllib2.Request(url, data, headers)
    request.get_method = lambda: method
    response = urllib2.urlopen(request)
    body = response.read()

    result = json.loads(body)
    if result.get('status') != 'success':
        if result.get('type') == 'ObjectMissingException':
            raise ObjectMissingException(result.get('message'))

        raise ApiCallFailedException('API Call Failed: ' + str(body))

    data = result.get('data')
    return data


class TestSimpleApi(unittest.TestCase):
    def assertDictContainsDict(self, smaller, bigger, exclude_keys=None):
        exclude_keys = exclude_keys or []
        for key in smaller:
            if key in exclude_keys:
                continue

            self.assertEqual(bigger.get(key), smaller.get(key))

    def list_fruit(self, cursor=None, limit=None):
        querystring = {}
        if limit:
            querystring['limit'] = limit
        if cursor:
            querystring['cursor'] = cursor

        logging.info('Listing fruit with cursor ' + str(cursor))

        data = call_json_api(api_root + "Fruit/search", query_string=querystring)
        return data['models'], data['cursor']

    def delete_fruit(self, id_):
        return call_json_api(api_root + "Fruit/{0}".format(id_), method="DELETE")

    def create_fruit(self, data):
        return call_json_api(api_root + "Fruit", payload=data, method="POST")

    def get_fruit(self, id_):
        return call_json_api(api_root + "Fruit/{0}".format(id_))

    def modify_fruit(self, id_, data):
        return call_json_api(api_root + "Fruit/{0}".format(id_), payload=data, method="PUT")

    def test_delete_all_fruit(self):
        limit = 2
        (fruits, cursor) = self.list_fruit(limit=2)
        for fruit in fruits:
            self.delete_fruit(fruit['id'])

        while cursor:
            (fruits, cursor) = self.list_fruit(cursor=cursor, limit=limit)
            for fruit in fruits:
                self.delete_fruit(fruit['id'])

        fruits, cursor = self.list_fruit()
        self.assertFalse(fruits, "There should be no fruits after running test_delete_all_fruit")

    def test_CRUD(self):
        self.skipTest("Skipping CRUD for now.")
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

        #CREATE
        new_id = self.create_fruit(data)

        #READ
        created = self.get_fruit(new_id)
        self.assertDictContainsDict(data, created)

        #UPDATE
        created["width"] = 20
        updated_id = self.modify_fruit(created['id'], created)
        self.assertEquals(new_id, updated_id, "New and Updated IDs don't match")
        updated_model = self.get_fruit(updated_id)
        self.assertDictContainsDict(created, updated_model,
                                    exclude_keys=['modified_datetime', 'modified_date', 'modified_time'])

        #DELETE
        self.delete_fruit(updated_id)
        try:
            result = self.get_fruit(new_id)
            self.assertFalse(True, "Fruit with id {0} should have been deleted!".format(new_id))
        except ObjectMissingException:
            pass
