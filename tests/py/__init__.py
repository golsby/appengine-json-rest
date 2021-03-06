import unittest
import uuid
from appengine_json_rest.clients.py import JSONClient, BasicAuthJSONClient
from appengine_json_rest.clients.py import ForbiddenError, ObjectMissingError, AuthenticationRequiredError


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

    def test_delete_all_fruit(self):
        # self.skipTest("Performance")
        limit = 10
        Fruit = JSONClient("Fruit", api_root)
        Q = Fruit.all()
        fruits = Q.fetch(limit)
        while fruits:
            for fruit in fruits:
                Fruit.delete(fruit['id'])
            fruits = Q.fetch()

        fruits = Fruit.all().fetch()
        self.assertFalse(fruits, "There should be no fruits after running test_delete_all_fruit")

    def test_CRUD(self):
        # self.skipTest("Performance")
        basket = {
            "location": {"lat": 10, "lon": 5}
        }

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
        Basket = JSONClient("Basket", api_root)

        #CREATE
        basket_obj = Basket.create(basket)
        data['basket'] = basket_obj
        created = Fruit.create(data)

        self.assertDictContainsDict(data, created, exclude_keys=['basket'])
        self.assertDictContainsDict(data['basket'], created['basket'], exclude_keys=['location'])

        #UPDATE
        created["width"] = 20
        updated_model = Fruit.update(created['id'], created)
        self.assertDictContainsDict(created, updated_model,
                                    exclude_keys=['modified_datetime', 'modified_date', 'modified_time'])

        #DELETE
        id_ = updated_model.get('id')
        Fruit.delete(id_)
        Basket.delete(basket_obj.get('id'))
        try:
            result = Fruit.read(id_)
            self.assertFalse(True, "Fruit with id {0} should have been deleted!".format(id_))
        except ObjectMissingError:
            pass

    def test_search(self):
        # self.skipTest("Performance")
        name1 = str(uuid.uuid4())
        name2 = str(uuid.uuid4())
        create_count = 5
        limit = 10
        F = JSONClient('Fruit', api_root)
        created_models = []
        for i in range(0, create_count):
            created_models.append(F.create({'name': name1, 'width': i}))
            created_models.append(F.create({'name': name2, 'width': i}))

        # Make sure we get create_count models back
        Q = F.all().filter('name =', name1).order('created_datetime', descending=True)
        models = Q.fetch(limit)
        self.assertEquals(len(models), create_count)

        # Make sure we get a cursor when fetching less than all of them
        Q = F.all().filter('name =', name1).order('created_datetime', descending=True)
        models = Q.fetch(create_count / 3)
        self.assertNotEqual(len(models), 0)

        while models:
            models = Q.fetch()

        # Clean up
        for model in created_models:
            F.delete(model.get('id'))

        # Make sure none are left:
        models = F.all().filter('name =', name1).fetch()
        self.assertEqual(len(models), 0)
        models = F.all().filter('name =', name2).fetch()
        self.assertEqual(len(models), 0)


class TestAuthApi(unittest.TestCase):
    def test_auth(self):
        #self.skipTest("Performance")
        # Server expects HTTP Basic Authentication
        AuthFruit = BasicAuthJSONClient('Fruit', auth_api_root, username='naive', password='pa$sw0rd')
        fruits = AuthFruit.all().fetch()

        # Server expects basic authentication; should raise HTTP 401 error
        # if no authentication information is passed.
        NoAuthFruit = BasicAuthJSONClient('Fruit', auth_api_root)
        self.assertRaises(AuthenticationRequiredError, NoAuthFruit.all().fetch)

        # Incorrect credentials should raise HTTP 401 error
        NoAuthFruit = BasicAuthJSONClient('Fruit', auth_api_root, username='incorrect', password='wrong')
        self.assertRaises(ForbiddenError, NoAuthFruit.all().fetch)


