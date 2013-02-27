__author__ = 'Brian'


class ApiFailureError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ObjectMissingError(ApiFailureError):
    pass


class HttpsRequiredError(ApiFailureError):
    def __init__(self):
        self.value = "https is required"

    def __str__(self):
        return repr(self.value)


class ForbiddenError(ApiFailureError):
    def __init__(self):
        self.value = "authentication failed"

    def __str__(self):
        return repr(self.value)


class AuthenticationRequiredError(ApiFailureError):
    def __init__(self, headers=None):
        self.headers = headers

    def __str__(self):
        return repr(self.headers)



class ModelNotRegisteredError(ApiFailureError):
    def __init__(self, value):
        super(ModelNotRegisteredError, self).__init__('Model "{0}" not registered'.format(value))