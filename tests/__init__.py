import unittest
import urllib2
import json

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


def urlencode_multidict(dict):
    if not dict:
        return None
    import urllib
    utf8dict = encode_multidict_as_utf8(dict)
    return urllib.urlencode(utf8dict, doseq=True)


class ApiCallFailedException(Exception):
    """ API Call Failed. """
    def __init__(self, value): # real signature unknown
        self.value = value

    def __str__(self):
        return repr(self.value)


def call_json_api(api_path, query_string=None, payload=None, method='GET'):
    import urllib
    data = None
    if payload:
        data = json.dumps(payload)
    query_string = urlencode_multidict(query_string)
    #utf8_data = unicode(data).encode('utf-8')
    # urlencoded_data = urllib.urlencode(utf8_data)
    url = api_path

    if method == 'GET' and query_string:
        url += "?" + query_string

    headers = {'Content-Type': 'application/json'}

    request = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(request)
    body = response.read()

    result = json.loads(body)
    if result.get('status') != 'success':
        raise ApiCallFailedException('API Call Failed: ' + str(body))

    data = result.get('data')
    return data


class TestSimpleApi(unittest.TestCase):
    def x_test_list_fruit(self):
        data = call_json_api(api_root + "Fruit/search")
        for fruit in data.get('models'):
            pass

    def test_create_fruit(self):
        data = {
            "name": "Banana",
            "width": 5,
            "location": {"lat": 22.3, "lon": 13.0},
            "destinations": [
                {"lat": 0, "lon": 0},
                {"lat": 1, "lon": 2},
                {"lat": 3.4, "lon": 5.6},
                {"lat": "7", "lon": "8.9"},
            ],
            "touched_dates": [
                "2012-01-03T15:32:00",
                "2012-01-04T17:01:16",
                "2012-01-07T00:01:02",
            ]
        }

        response = call_json_api(api_root + "Fruit", payload=data, method="POST")