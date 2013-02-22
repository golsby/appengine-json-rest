__author__ = 'Brian'


class ObjectMissingError(Exception):
    pass


class ApiFailureError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class HttpsRequiredError(ApiFailureError):
    def __init__(self):
        self.value = "https is required"

    def __str__(self):
        return repr(self.value)


class AuthenticationFailedError(ApiFailureError):
    def __init__(self):
        self.value = "authentication failed"

    def __str__(self):
        return repr(self.value)


class AuthenticationRequiredError(ApiFailureError):
    pass


class ModelNotRegisteredError(ApiFailureError):
    def __init__(self, value):
        super(ModelNotRegisteredError, self).__init__('Model "{0}" not registered'.format(value))