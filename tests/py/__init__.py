import unittest
import urllib2
from appengine_json_rest.clients.py import JSONClient, AuthenticationFailedError, ObjectMissingError, Query


# These tests are designed to work with the sample
# AppEngine project wrapping the appengine_json_rest module.
# https://github.com/golsby/appengine-json-rest-sample

api_host = "localhost:5000"
api_root = "http://{0}/simple/".format(api_host)
auth_api_root = "http://{0}/private/".format(api_host)


class TestSimpleApi(unittest.TestCase):
    def assertDictContainsDict(self, smaller, bigger, exclude_keys=None):
        exclude_keys = exclude_keys or []
        for key in smaller:
            if key in exclude_keys:
                continue

            self.assertEqual(bigger.get(key), smaller.get(key))

    def xtest_delete_all_fruit(self):
        self.skipTest("speed up")
        limit = 2
        Fruit = JSONClient("Fruit", api_root)
        (fruits, cursor) = Fruit.search(limit=limit)
        for fruit in fruits:
            Fruit.delete(fruit['id'])

        while cursor:
            (fruits, cursor) = Fruit.search(limit=limit, cursor=cursor)
            for fruit in fruits:
                Fruit.delete(fruit['id'])

        fruits, cursor = Fruit.search()
        self.assertFalse(fruits, "There should be no fruits after running test_delete_all_fruit")

    def xtest_CRUD(self):
        self.skipTest("speed up")
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

        Fruit = JSONClient("Fruit", api_root)

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
        except ObjectMissingError:
            pass

    def xtest_auth(self):
        # Server expects HTTP Basic Authentication
        AuthFruit = JSONClient('Fruit', auth_api_root, username='naive', password='pa$sw0rd')
        fruits, cursor = AuthFruit.search()

        # Server expects basic authentication; should raise HTTP 401 error
        # if no authentication information is passed.
        NoAuthFruit = JSONClient('Fruit', auth_api_root)
        self.assertRaises(urllib2.HTTPError, NoAuthFruit.search)

        # Incorrect credentials should raise HTTP 401 error
        NoAuthFruit = JSONClient('Fruit', auth_api_root, username='incorrect', password='wrong')
        self.assertRaises(AuthenticationFailedError, NoAuthFruit.search)

    def test_search(self):
        F = JSONClient('Fruit', api_root)
        #for i in range(0, 5):
        #    F.create({'name': 'Banana', 'width': i})
        #    F.create({'name': 'Apple', 'width': i})

        Q = Query(F).filter('name =', 'Apple').order('created_datetime')
        (models, cursor) = Q.fetch(2)
        while cursor:
            Q = Query(F).filter('name =', 'Apple').order('created_datetime').with_cursor(cursor)
            models, cursor = Q.fetch(2)
        pass
