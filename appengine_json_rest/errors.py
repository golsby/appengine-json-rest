__author__ = 'Brian'


class ObjectMissingException(Exception):
    pass


class ApiFailureException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class HttpsRequiredException(ApiFailureException):
    def __init__(self):
        self.value = "https is required"
    def __str__(self):
        return repr(self.value)


class AuthenticationFailedException(ApiFailureException):
    def __init__(self):
        self.value = "authentication failed"
    def __str__(self):
        return repr(self.value)


class ModelNotRegisteredException(ApiFailureException):
    def __init__(self, value):
        super(ModelNotRegisteredException, self).__init__('Model "{0}" not registered'.format(value))